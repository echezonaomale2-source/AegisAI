"""Compute module metrics from counters, path logs, and research tables."""

from __future__ import annotations

import json
from collections import Counter

from memory.database import connect
from evaluation.counters import EvalCounters
from evaluation.models import (
    CalibrationMetrics,
    DecisionMetrics,
    EvidenceMetrics,
    FeatureMetrics,
    KnowledgeMetrics,
    LearningMetrics,
    TradeReviewMetrics,
    VisionMetrics,
)
from research.confidence_calibration import ConfidenceCalibrationEngine
from research.database import init_research_db
from knowledge.versioning import CURRENT_VERSION

init_research_db()


def _rate(part: float, whole: float) -> float | None:
    if whole <= 0:
        return None
    return round(min(100.0, 100.0 * part / whole), 2)


class MetricsCollector:
    def __init__(self) -> None:
        self.counters = EvalCounters()
        self.calibration_engine = ConfidenceCalibrationEngine()

    def vision(self) -> VisionMetrics:
        c = self.counters
        accepted = int(c.get("vision.accepted"))
        rejected = int(c.get("vision.rejected"))
        total = accepted + rejected
        conf_sum = c.get("vision.confidence_sum")
        conf_n = c.get("vision.confidence_n")
        return VisionMetrics(
            images_accepted=accepted,
            images_rejected=rejected,
            avg_detection_confidence=round(conf_sum / conf_n, 2) if conf_n else None,
            timeframe_detections=int(c.get("vision.timeframe_known")),
            pair_detections=int(c.get("vision.pair_known")),
            structure_detections=int(c.get("vision.structure_known")),
            unknown_detections=int(c.get("vision.unknown")),
            false_detections_verified=int(c.get("vision.false_verified")),
            accept_rate=_rate(accepted, total),
        )

    def features(self) -> FeatureMetrics:
        events = self.counters.feature_events()
        by_key = {e["feature_key"]: e for e in events}
        total_det = sum(e["detections"] for e in events) or 0
        total_unk = sum(e["unknowns"] for e in events) or 0

        def rate(key: str) -> float | None:
            row = by_key.get(key)
            if not row or total_det <= 0:
                # rate among analyses that recorded any features
                analyses = self.counters.get("decision.total")
                if analyses <= 0:
                    return None
                return _rate(row["detections"] if row else 0, analyses)
            analyses = self.counters.get("decision.total") or total_det
            return _rate(row["detections"], analyses)

        return FeatureMetrics(
            trend_detection_rate=rate("trend"),
            bos_detection_rate=rate("bos"),
            choch_detection_rate=rate("choch"),
            liquidity_detection_rate=rate("liquidity"),
            order_block_detection_rate=_combine_rate(by_key, ["bullish_order_block", "bearish_order_block"], self.counters.get("decision.total")),
            fvg_detection_rate=_combine_rate(by_key, ["bullish_fvg", "bearish_fvg"], self.counters.get("decision.total")),
            supply_detection_rate=rate("supply_zone"),
            demand_detection_rate=rate("demand_zone"),
            unknown_rate=_rate(total_unk, total_det + total_unk) if (total_det + total_unk) else None,
            total_feature_events=total_det,
        )

    def knowledge(self) -> KnowledgeMetrics:
        c = self.counters
        validated = c.get("knowledge.validated")
        rejected = c.get("knowledge.rejected")
        total = validated + rejected
        return KnowledgeMetrics(
            concepts_validated=int(validated),
            concepts_rejected=int(rejected),
            unknown_rate=_rate(rejected, total),
            knowledge_version=CURRENT_VERSION,
        )

    def evidence(self) -> EvidenceMetrics:
        c = self.counters
        n = c.get("evidence.samples")
        if n <= 0:
            return EvidenceMetrics()
        buy = c.get("evidence.buy_sum") / n
        sell = c.get("evidence.sell_sum") / n
        neu = c.get("evidence.neutral_sum") / n
        # Consistency: share of mass on the dominant side
        dominant = max(buy, sell, neu)
        total = buy + sell + neu
        consistency = (100.0 * dominant / total) if total > 0 else None
        return EvidenceMetrics(
            avg_buy_weight=round(buy, 2),
            avg_sell_weight=round(sell, 2),
            avg_neutral_weight=round(neu, 2),
            consistency_score=round(consistency, 2) if consistency is not None else None,
        )

    def decisions(self) -> DecisionMetrics:
        c = self.counters
        buy = int(c.get("decision.buy"))
        sell = int(c.get("decision.sell"))
        no_trade = int(c.get("decision.no_trade"))
        total = buy + sell + no_trade
        conf_sum = c.get("decision.confidence_sum")
        conf_n = c.get("decision.confidence_n")
        rr_sum = c.get("decision.rr_sum")
        rr_n = c.get("decision.rr_n")

        dist: dict[str, int] = {}
        for label, lo, hi in [
            ("0-50", 0, 50),
            ("50-70", 50, 70),
            ("70-85", 70, 85),
            ("85-100", 85, 101),
        ]:
            dist[label] = int(c.get(f"decision.conf_bin.{label}"))

        return DecisionMetrics(
            buy_recommendations=buy,
            sell_recommendations=sell,
            no_trade_recommendations=no_trade,
            average_confidence=round(conf_sum / conf_n, 2) if conf_n else None,
            confidence_distribution=dist,
            average_risk_reward=round(rr_sum / rr_n, 3) if rr_n else None,
            total_decisions=total,
        )

    def calibration(self) -> CalibrationMetrics:
        state = self.calibration_engine.state()
        return CalibrationMetrics(
            sample_count=state.sample_count,
            global_gap=state.global_gap,
            adjustment_factor=state.adjustment_factor,
            expected_calibration_error=state.expected_calibration_error,
            bins=[b.model_dump() for b in state.bins],
            notes=list(state.notes),
        )

    def trade_reviews(self) -> TradeReviewMetrics:
        with connect() as conn:
            rows = conn.execute(
                "SELECT scorecard_json, outcome, decision_quality FROM research_reviews"
            ).fetchall()
        if not rows:
            # fallback memories
            with connect() as conn:
                wins = conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE outcome = 'TAKE_PROFIT'"
                ).fetchone()["c"]
                losses = conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE outcome = 'STOP_LOSS'"
                ).fetchone()["c"]
            return TradeReviewMetrics(
                winning_analyses=int(wins),
                losing_analyses=int(losses),
                completed_reviews=0,
            )

        wins = losses = 0
        overall_scores: list[float] = []
        entry_scores: list[float] = []
        sl_scores: list[float] = []
        tp_scores: list[float] = []
        htf_scores: list[float] = []
        quality_dist: dict[str, int] = {}

        for row in rows:
            if row["outcome"] in {"TAKE_PROFIT", "TP"}:
                wins += 1
            elif row["outcome"] in {"STOP_LOSS", "SL"}:
                losses += 1
            dq = row["decision_quality"] if "decision_quality" in row.keys() else None
            if dq:
                quality_dist[str(dq)] = quality_dist.get(str(dq), 0) + 1
            try:
                sc = json.loads(row["scorecard_json"] or "{}")
            except json.JSONDecodeError:
                continue
            if "overall_analysis_quality" in sc:
                overall_scores.append(float(sc["overall_analysis_quality"]))
            if "entry_quality" in sc:
                entry_scores.append(float(sc["entry_quality"]))
            if "stop_loss_placement" in sc:
                sl_scores.append(float(sc["stop_loss_placement"]))
            if "take_profit_placement" in sc:
                tp_scores.append(float(sc["take_profit_placement"]))
            if "higher_timeframe_alignment" in sc:
                htf_scores.append(float(sc["higher_timeframe_alignment"]))

        def avg(xs: list[float]) -> float | None:
            return round(sum(xs) / len(xs), 2) if xs else None

        return TradeReviewMetrics(
            winning_analyses=wins,
            losing_analyses=losses,
            average_review_score=avg(overall_scores),
            avg_entry_quality=avg(entry_scores),
            avg_stop_loss_quality=avg(sl_scores),
            avg_take_profit_quality=avg(tp_scores),
            avg_htf_alignment_quality=avg(htf_scores),
            completed_reviews=len(rows),
            decision_quality_distribution=quality_dist,
        )

    def learning(self) -> LearningMetrics:
        c = self.counters
        with connect() as conn:
            memories = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
            lessons = conn.execute(
                "SELECT COUNT(*) AS c FROM research_lessons"
            ).fetchone()["c"]
            patterns = conn.execute(
                "SELECT COUNT(*) AS c FROM research_patterns"
            ).fetchone()["c"]
            closed = conn.execute(
                """
                SELECT
                  SUM(CASE WHEN outcome = 'TAKE_PROFIT' THEN 1 ELSE 0 END) AS wins,
                  SUM(CASE WHEN outcome = 'STOP_LOSS' THEN 1 ELSE 0 END) AS losses
                FROM memories
                WHERE outcome IN ('TAKE_PROFIT', 'STOP_LOSS')
                """
            ).fetchone()
        wins = int(closed["wins"] or 0)
        losses = int(closed["losses"] or 0)
        closed_n = wins + losses
        effectiveness = round(100.0 * wins / closed_n, 2) if closed_n >= 10 else None
        notes = []
        if closed_n < 10:
            notes.append("Learning effectiveness warming up (<10 closed trades).")
        elif effectiveness is not None:
            notes.append(f"Closed-trade win rate proxy: {effectiveness}% (n={closed_n}).")
        return LearningMetrics(
            pattern_statistics_updated=int(c.get("learning.pattern_updates") or patterns),
            confidence_adjustments_made=int(c.get("learning.confidence_adjustments")),
            lessons_generated=int(c.get("learning.lessons") or lessons),
            memory_growth=int(memories),
            similarity_searches=int(c.get("learning.similarity_searches")),
            effectiveness_score=effectiveness,
            notes=notes,
        )


def _combine_rate(by_key: dict, keys: list[str], analyses: float) -> float | None:
    if analyses <= 0:
        return None
    total = sum((by_key.get(k) or {}).get("detections", 0) for k in keys)
    return _rate(total, analyses)
