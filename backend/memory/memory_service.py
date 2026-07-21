"""Orchestrates memory, review, patterns, learning, and confidence adjustment."""

from __future__ import annotations

import json
from pathlib import Path

from memory.confidence_adjuster import ConfidenceAdjuster
from memory.feature_fingerprint import build_fingerprint
from memory.learning_engine import LearningEngine
from memory.lesson_generator import LessonGenerator
from memory.memory_repository import MemoryRepository
from memory.memory_stats import MemoryStatsService
from memory.outcome_utils import is_neutral, normalize_outcome
from memory.pattern_engine import PatternEngine, pattern_key_from_bits
from memory.performance_engine import PerformanceEngine
from memory.review_engine import ReviewEngine
from memory.similarity_engine import SimilarityEngine
from models.decision_schemas import TradeDecision


class MemoryService:
    def __init__(self) -> None:
        self.repo = MemoryRepository()
        self.similarity = SimilarityEngine()
        self.adjuster = ConfidenceAdjuster()
        self.learning = LearningEngine()
        self.lessons = LessonGenerator()
        self.stats = MemoryStatsService()
        self.review_engine = ReviewEngine()
        self.pattern_engine = PatternEngine()
        self.performance = PerformanceEngine()

    def remember_decision(
        self,
        decision: TradeDecision,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
    ) -> TradeDecision:
        fingerprint = build_fingerprint(decision)
        self.repo.upsert_memory(
            {
                "trade_id": decision.trade_id,
                "timestamp": decision.generated_at,
                "pair": decision.pair,
                "timeframes": decision.timeframes,
                "chart_4h_path": str(chart_4h),
                "chart_1h_path": str(chart_1h),
                "chart_15m_path": str(chart_15m),
                "features": fingerprint["features"],
                "analysis_4h": decision.analysis_4h.model_dump(),
                "analysis_1h": decision.analysis_1h.model_dump(),
                "analysis_15m": decision.analysis_15m.model_dump(),
                "final_decision": decision.overall_bias,
                "entry": decision.entry,
                "stop_loss": decision.stop_loss,
                "take_profit": decision.take_profit,
                "risk_reward": decision.risk_reward,
                "confidence": decision.confidence,
                "explanation": decision.explanation,
                "status": decision.status,
                "fingerprint_bits": fingerprint["bits"],
                "fingerprint_hash": fingerprint["hash"],
                "direction": decision.overall_bias,
            }
        )
        return decision

    def apply_memory_to_decision(self, decision: TradeDecision) -> TradeDecision:
        """Search similar memories + patterns and adjust confidence."""
        fingerprint = build_fingerprint(decision)

        if decision.overall_bias == "NO TRADE":
            decision.warnings = list(decision.warnings) + [
                "NO TRADE is a valid professional outcome when evidence is insufficient."
            ]
            # Still attach pattern context if available.
            pattern = self.pattern_engine.get(fingerprint["bits"])
            if pattern and pattern["trades"]:
                decision.warnings.append(
                    f"Related pattern history: {pattern['trades']} trades, "
                    f"win rate {pattern.get('win_rate')}%."
                )
            return decision

        report = self.similarity.find_similar(
            fingerprint["bits"],
            direction=decision.overall_bias,
            pair=decision.pair,
        )
        adjustment = self.adjuster.adjust(
            decision.confidence,
            report,
            decision=decision,
            fingerprint_bits=fingerprint["bits"],
        )

        decision.warnings = list(decision.warnings)
        decision.warnings.append(adjustment.reason)
        if report.win_rate is not None:
            decision.warnings.append(
                f"Similar setups: {adjustment.similar_count} closed "
                f"(TP {adjustment.tp_count} / SL {adjustment.sl_count})."
            )

        if adjustment.applied:
            decision.confidence = adjustment.adjusted_confidence
            decision.confidence_scorecard.overall = adjustment.adjusted_confidence
            factor_lines = ", ".join(
                f"{k}={v:.0f}" for k, v in list(adjustment.factors.items())[:4]
            )
            decision.explanation = (
                decision.explanation
                + "\n\nMemory Evidence\n"
                + f"- {adjustment.reason}\n"
                + f"- Factors: {factor_lines}"
            )
            if adjustment.historical_win_rate is not None and adjustment.similar_count:
                decision.reasons = list(decision.reasons) + [
                    f"Historical similar win rate: {adjustment.historical_win_rate:.1f}% "
                    f"across {adjustment.similar_count} trades."
                ]

        return decision

    def learn_from_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart_path: str | None,
        decision: TradeDecision | None = None,
    ) -> dict:
        outcome = normalize_outcome(outcome)
        memory = self.repo.get(trade_id)
        if memory is None:
            raise ValueError(f"Memory not found for trade {trade_id}")

        # Idempotency — never double-count pattern/feature stats for the same trade.
        existing = memory.get("outcome")
        if existing:
            return {
                "trade_id": trade_id,
                "outcome": existing,
                "lesson": memory.get("lesson"),
                "lessons": [],
                "grade": memory.get("grade"),
                "skipped": True,
                "reason": "outcome_already_recorded",
                "learning_applied": False,
                "learning_update": self.learning.get_adaptive_weights(),
                "memory": memory,
            }

        if decision is None:
            decision = self._rebuild_decision(memory, trade_id)

        # Phase 4.5: full post-trade case study.
        review = self.review_engine.review(
            decision,
            outcome=outcome,
            outcome_chart_path=outcome_chart_path,
        )
        performance = self.performance.classify(review.scorecard)
        lesson_list = self.lessons.generate_lessons(decision, outcome, review)
        primary_lesson = lesson_list[0]

        rr_value = None
        try:
            rr_value = float(str(decision.risk_reward).replace(",", ""))
        except ValueError:
            rr_value = None

        pattern = self.pattern_engine.record(
            memory["fingerprint_bits"],
            outcome=outcome,
            risk_reward=rr_value,
            confidence=float(decision.confidence or 0),
        )

        self.repo.save_review(
            trade_id,
            grade=review.grade,
            scorecard=review.scorecard.as_dict(),
            critique=review.critique.as_dict(),
            questions=review.questions,
            lessons=lesson_list,
            summary=review.summary,
            outcome_analysis=(
                review.outcome_analysis.model_dump() if review.outcome_analysis else None
            ),
        )

        updated = self.repo.update_outcome(
            trade_id,
            outcome=outcome,
            outcome_chart_path=outcome_chart_path,
            lesson=primary_lesson,
            grade=review.grade,
            review_json=json.dumps(review.as_dict()),
            lessons_json=json.dumps(lesson_list),
            pattern_key=pattern_key_from_bits(memory["fingerprint_bits"]),
        )

        # Never learn blindly — gate by review quality. BREAK_EVEN skips win/loss.
        strength = (
            0.0
            if is_neutral(outcome)
            else float(performance["learning_strength"])
            if performance["should_influence_learning"]
            else 0.1
        )
        self.learning.record_outcome(
            memory["fingerprint_bits"],
            outcome,
            learning_strength=strength,
        )

        return {
            "trade_id": trade_id,
            "outcome": outcome,
            "lesson": primary_lesson,
            "lessons": lesson_list,
            "grade": review.grade,
            "grade_label": performance["label"],
            "scorecard": review.scorecard.as_dict(),
            "critique": review.critique.as_dict(),
            "questions": review.questions,
            "review_summary": review.summary,
            "pattern": pattern,
            "memory": updated,
            "learning_update": self.learning.get_adaptive_weights(),
            "learning_applied": bool(performance["should_influence_learning"] and not is_neutral(outcome)),
            "learning_strength": strength,
            "skipped": False,
            "fingerprint_bits": memory["fingerprint_bits"],
        }

    def _rebuild_decision(self, memory: dict, trade_id: str) -> TradeDecision:
        from models.chart_schemas import ChartAnalysis
        from models.decision_schemas import ConfidenceScorecard, TradeDecision as TD

        return TD(
            pair=memory["pair"],
            timeframes=json.loads(memory["timeframes_json"] or "{}"),
            analysis_4h=ChartAnalysis.model_validate(json.loads(memory["analysis_4h_json"])),
            analysis_1h=ChartAnalysis.model_validate(json.loads(memory["analysis_1h_json"])),
            analysis_15m=ChartAnalysis.model_validate(json.loads(memory["analysis_15m_json"])),
            overall_bias=memory["direction"],
            entry=memory["entry"] or "—",
            stop_loss=memory["stop_loss"] or "—",
            take_profit=memory["take_profit"] or "—",
            risk_reward=memory["risk_reward"] or "—",
            target_liquidity="None",
            confidence=float(memory["confidence"] or 0),
            confidence_scorecard=ConfidenceScorecard(
                htf_4h_alignment=0,
                mtf_1h_alignment=0,
                ltf_15m_confirmation=0,
                liquidity=0,
                order_block=0,
                fair_value_gap=0,
                market_structure=0,
                overall=float(memory["confidence"] or 0),
                weights={},
            ),
            explanation=memory["explanation"] or "",
            reasons=[],
            warnings=[],
            trade_id=trade_id,
            generated_at=memory["timestamp"],
        )

    def get_stats(self) -> dict:
        return self.stats.build()
