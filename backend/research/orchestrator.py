"""
Research orchestrator — wires review, calibration, patterns, lessons.

Does not replace MemoryService; runs alongside after outcomes and
wraps decisions with self-checks + calibration.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.logging_setup import get_logger
from memory.database import connect
from memory.feature_fingerprint import build_fingerprint
from memory.memory_service import MemoryService
from memory.outcome_utils import counts_toward_calibration, normalize_outcome
from models.decision_schemas import TradeDecision
from models.schemas import utc_now_iso
from research.analysis_cache import AnalysisCache
from research.confidence_calibration import ConfidenceCalibrationEngine
from research.database import init_research_db
from research.lesson_engine import LessonEngine
from research.models import ReviewReport
from research.pattern_library import PatternLibrary
from research.post_trade_review import PostTradeReviewEngine
from research.self_checks import SelfCheckEngine

log = get_logger("research.orchestrator")
init_research_db()


class ResearchOrchestrator:
    def __init__(self) -> None:
        self.memory = MemoryService()
        self.review = PostTradeReviewEngine()
        self.calibration = ConfidenceCalibrationEngine()
        self.patterns = PatternLibrary()
        self.lessons = LessonEngine()
        self.self_checks = SelfCheckEngine(
            calibration=self.calibration,
            patterns=self.patterns,
        )
        self.cache = AnalysisCache()
        self.archive_root = (
            Path(__file__).resolve().parent.parent / "storage" / "cognitive_archive"
        )

    def apply_pre_decision_gates(self, decision: TradeDecision) -> TradeDecision:
        """Self-checks + confidence calibration before persist."""
        calibrated = self.calibration.adjust(decision.confidence)
        fingerprint = build_fingerprint(decision)
        features = list(fingerprint.get("active_features") or [])
        checks = self.self_checks.check(decision, feature_keys=features)

        warnings = list(decision.warnings)
        warnings.extend(checks.warnings)
        warnings.append(f"Calibrated confidence: {calibrated:.1f}% (raw {decision.confidence:.1f}%).")
        for c in checks.checks:
            warnings.append(f"Self-check [{c['name']}]: {'pass' if c['passed'] else 'fail'} — {c['detail']}")

        updates: dict[str, Any] = {
            "confidence": calibrated,
            "warnings": warnings,
        }

        if decision.overall_bias == "NO TRADE":
            reason = _primary_no_trade_reason(decision.explanation, warnings)
            self._bump_counter("research_no_trade_reasons", reason)
        elif checks.force_no_trade:
            updates.update(
                {
                    "overall_bias": "NO TRADE",
                    "entry": "—",
                    "stop_loss": "—",
                    "take_profit": "—",
                    "risk_reward": "—",
                    "explanation": (
                        decision.explanation
                        + " Self-check forced NO TRADE — evidence or calibration insufficient."
                    ),
                }
            )
            self._bump_counter("research_no_trade_reasons", "Failed self-check")

        return decision.model_copy(update=updates)

    def process_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart_path: str | None,
    ) -> dict[str, Any]:
        """Legacy memory learn + research review / calibration / patterns / lessons."""
        outcome = normalize_outcome(outcome)

        # Idempotency at research layer (memory also guards).
        prior = self.memory.repo.get(trade_id)
        if prior and prior.get("outcome"):
            return {
                "trade_id": trade_id,
                "outcome": prior.get("outcome"),
                "skipped": True,
                "reason": "outcome_already_recorded",
                "learning_applied": False,
                "research": None,
            }

        learned = self.memory.learn_from_outcome(
            trade_id,
            outcome=outcome,
            outcome_chart_path=outcome_chart_path,
        )
        if learned.get("skipped"):
            return {**learned, "research": None}

        memory = self.memory.repo.get(trade_id)
        if memory is None:
            return {**learned, "research": None}

        decision = self.memory._rebuild_decision(memory, trade_id)  # noqa: SLF001

        cognitive = self._load_cognitive_archive(trade_id)
        legacy_review = {
            "scorecard": learned.get("scorecard"),
            "critique": learned.get("critique"),
        }
        report = self.review.review(
            trade_id,
            outcome=outcome,
            decision=decision,
            outcome_chart=Path(outcome_chart_path) if outcome_chart_path else None,
            cognitive_archive=cognitive,
            legacy_review=legacy_review,
        )
        lesson_list = self.lessons.from_review(report)
        self.lessons.store(trade_id, lesson_list)

        # Calibration: never move on BREAK_EVEN; TP/SL only for directional trades.
        if (
            decision.overall_bias in {"BUY", "SELL"}
            and counts_toward_calibration(outcome)
        ):
            success = outcome == "TAKE_PROFIT"
            cal_state = self.calibration.record(decision.confidence, success=success)
        else:
            cal_state = self.calibration.state()

        fingerprint = build_fingerprint(decision)
        feature_keys = list(fingerprint.get("active_features") or [])
        rr = _parse_rr(decision.risk_reward)
        pattern = self.patterns.record_outcome(
            feature_keys,
            outcome=outcome,
            confidence=decision.confidence,
            risk_reward=rr,
            was_no_trade=decision.overall_bias == "NO TRADE",
        )

        # Cognitive feature-weight nudge (incremental; requires explicit features).
        try:
            from cognitive.container import get_cognitive_container

            cog = get_cognitive_container().learning.apply_incremental_update(
                outcome=outcome,
                feature_types=feature_keys,
                grade=str(learned.get("grade") or "C"),
                learning_strength=float(learned.get("learning_strength") or 0.0),
            )
            learned["cognitive_weight_updates"] = cog
        except Exception as exc:  # noqa: BLE001
            log.debug("cognitive learning nudge skipped: %s", exc)

        if outcome == "STOP_LOSS":
            reason = report.weaknesses[0] if report.weaknesses else "Setup invalidated"
            self._bump_counter("research_loss_reasons", reason[:120])

        self._persist_review(report)

        # Phase 9 evaluation outcome attachment
        try:
            from evaluation.engine import EvaluationEngine

            EvaluationEngine().record_outcome(
                trade_id,
                outcome=outcome,
                review_scores=report.scorecard.model_dump(),
                lessons_count=len(lesson_list),
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("evaluation outcome hook skipped: %s", exc)

        log.info(
            "research outcome trade=%s quality=%s lessons=%d skipped=%s",
            trade_id,
            report.decision_quality,
            len(lesson_list),
            learned.get("skipped", False),
        )
        return {
            **learned,
            "research": {
                "review": report.model_dump(mode="json"),
                "decision_quality": report.decision_quality,
                "scorecard": report.scorecard.model_dump(mode="json"),
                "lessons": lesson_list,
                "calibration": cal_state.model_dump(mode="json"),
                "pattern": pattern.model_dump(mode="json"),
                "questions": report.questions,
                "strengths": report.strengths,
                "weaknesses": report.weaknesses,
            },
        }

    def learning_summary(self) -> dict[str, Any]:
        """Historical learning snapshot for dashboards (Step 8)."""
        from cognitive.container import get_cognitive_container

        cal = self.calibration.state()
        return {
            "calibration": cal.model_dump(mode="json"),
            "feature_reliability": self.memory.learning.feature_performance(),
            "adaptive_weights": self.memory.learning.get_adaptive_weights(),
            "top_patterns": self.memory.pattern_engine.top_patterns(8),
            "research_patterns": [
                p.model_dump(mode="json") for p in self.patterns.top_patterns(8)
            ],
            "recent_lessons": self.lessons.recent(8),
            "cognitive": get_cognitive_container().learning.historical_summary(),
            "memory_stats": self.memory.get_stats(),
        }

    def _load_cognitive_archive(self, trade_id: str) -> dict[str, Any] | None:
        path = self.archive_root / f"{trade_id}.json"
        if not path.exists():
            return None
        try:
            from core.security.encryption import get_encryptor

            raw = get_encryptor().decrypt_text(path.read_text(encoding="utf-8"))
            return json.loads(raw)
        except Exception:  # noqa: BLE001
            return None

    def _persist_review(self, report: ReviewReport) -> None:
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO research_reviews
                (trade_id, outcome, decision_quality, scorecard_json, report_json, cognitive_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    outcome = excluded.outcome,
                    decision_quality = excluded.decision_quality,
                    scorecard_json = excluded.scorecard_json,
                    report_json = excluded.report_json,
                    cognitive_hash = excluded.cognitive_hash
                """,
                (
                    report.trade_id,
                    report.outcome,
                    report.decision_quality,
                    json.dumps(report.scorecard.model_dump()),
                    json.dumps(report.model_dump(mode="json")),
                    report.cognitive_hash,
                    utc_now_iso(),
                ),
            )
            conn.commit()

    def _bump_counter(self, table: str, reason: str) -> None:
        now = utc_now_iso()
        key = (reason or "Unspecified")[:160]
        with connect() as conn:
            conn.execute(
                f"""
                INSERT INTO {table} (reason_key, count, last_seen)
                VALUES (?, 1, ?)
                ON CONFLICT(reason_key) DO UPDATE SET
                    count = count + 1,
                    last_seen = excluded.last_seen
                """,
                (key, now),
            )
            conn.commit()


def _parse_rr(value: str | None) -> float | None:
    if not value or value == "—":
        return None
    try:
        return float(str(value).replace(" ", "").split(":")[-1])
    except ValueError:
        return None


def _primary_no_trade_reason(explanation: str, warnings: list[str]) -> str:
    blob = (explanation + " " + " ".join(warnings)).lower()
    if "self-check" in blob:
        return "Failed self-check"
    if "uncertainty" in blob or "quality" in blob:
        return "Image uncertainty / quality"
    if "conflict" in blob:
        return "Conflicting evidence"
    if "confidence" in blob:
        return "Confidence below threshold"
    if "risk" in blob or "reward" in blob:
        return "Insufficient risk/reward"
    return "Insufficient evidence"
