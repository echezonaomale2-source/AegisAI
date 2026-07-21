"""
Evaluation Engine — record events, build reports, enforce improvement evidence.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from models.decision_schemas import TradeDecision
from models.schemas import utc_now_iso
from memory.database import connect
from evaluation.counters import EvalCounters
from evaluation.database import init_evaluation_db
from evaluation.health import HealthReporter
from evaluation.metrics import MetricsCollector
from evaluation.models import EvaluationReport
from evaluation.path_logger import DecisionPathLogger
from evaluation.quality_gates import ABTestService, QualityGateService
from knowledge.versioning import CURRENT_VERSION

init_evaluation_db()


class EvaluationEngine:
    def __init__(self) -> None:
        self.counters = EvalCounters()
        self.paths = DecisionPathLogger()
        self.metrics = MetricsCollector()
        self.health = HealthReporter()
        self.gates = QualityGateService()
        self.ab = ABTestService()

    def record_decision(
        self,
        decision: TradeDecision,
        *,
        validated_concepts: list[str] | None = None,
        evidence_summary: dict[str, Any] | None = None,
        reasoning_summary: dict[str, Any] | None = None,
        input_summary: dict[str, Any] | None = None,
        variant_id: str | None = None,
        chart_statuses: dict[str, str] | None = None,
    ) -> str:
        """Record metrics + decision path after a recommendation."""
        c = self.counters
        bias = decision.overall_bias
        if bias == "BUY":
            c.incr("decision.buy")
        elif bias == "SELL":
            c.incr("decision.sell")
        else:
            c.incr("decision.no_trade")
        c.incr("decision.total")
        c.incr("decision.confidence_sum", decision.confidence)
        c.incr("decision.confidence_n")
        conf = decision.confidence
        if conf < 50:
            c.incr("decision.conf_bin.0-50")
        elif conf < 70:
            c.incr("decision.conf_bin.50-70")
        elif conf < 85:
            c.incr("decision.conf_bin.70-85")
        else:
            c.incr("decision.conf_bin.85-100")

        rr = _parse_rr(decision.risk_reward)
        if rr is not None:
            c.incr("decision.rr_sum", rr)
            c.incr("decision.rr_n")

        # Vision-ish proxies from chart analyses
        for label, analysis in (
            ("4H", decision.analysis_4h),
            ("1H", decision.analysis_1h),
            ("15M", decision.analysis_15m),
        ):
            if analysis.status == "ok":
                c.incr("vision.accepted")
                c.incr("vision.confidence_sum", analysis.confidence)
                c.incr("vision.confidence_n")
                if analysis.pair and analysis.pair != "Unknown":
                    c.incr("vision.pair_known")
                else:
                    c.incr("vision.unknown")
                if analysis.timeframe and analysis.timeframe != "Unknown":
                    c.incr("vision.timeframe_known")
                else:
                    c.incr("vision.unknown")
                if analysis.market_structure and analysis.market_structure != "Unknown":
                    c.incr("vision.structure_known")
                else:
                    c.incr("vision.unknown")
                # Feature tallies
                if analysis.trend in {"Bullish", "Bearish", "Range"}:
                    c.record_feature("trend", detected=True)
                else:
                    c.record_feature("trend", detected=False, unknown=True)
                c.record_feature("bos", detected=bool(analysis.bos), unknown=not analysis.bos and analysis.market_structure == "Unknown")
                c.record_feature("choch", detected=bool(analysis.choch))
                c.record_feature(
                    "liquidity",
                    detected=analysis.liquidity not in {"None Detected", "Unknown", ""},
                )
                c.record_feature(
                    "bullish_order_block" if analysis.bullish_order_block else "bearish_order_block",
                    detected=analysis.bullish_order_block or analysis.bearish_order_block,
                )
                c.record_feature(
                    "bullish_fvg" if analysis.fvg_type == "Bullish FVG" else "bearish_fvg",
                    detected=bool(analysis.fair_value_gap),
                )
                c.record_feature("supply_zone", detected=bool(analysis.supply_zone))
                c.record_feature("demand_zone", detected=bool(analysis.demand_zone))
            else:
                c.incr("vision.rejected")

        concepts = validated_concepts or []
        if concepts:
            c.incr("knowledge.validated", len(concepts))
        # Knowledge rejects from missing notes
        for note in decision.warnings:
            if "Rejected" in note or "knowledge" in note.lower() and "unknown" in note.lower():
                c.incr("knowledge.rejected")

        if evidence_summary:
            c.incr("evidence.samples")
            c.incr("evidence.buy_sum", float(evidence_summary.get("buy_score", 0)))
            c.incr("evidence.sell_sum", float(evidence_summary.get("sell_score", 0)))
            c.incr("evidence.neutral_sum", float(evidence_summary.get("neutral_score", 0)))

        c.incr("learning.similarity_searches")  # apply_memory typically searches
        if any("Calibrated confidence" in w for w in decision.warnings):
            c.incr("learning.confidence_adjustments")

        path = self.paths.log(
            trade_id=decision.trade_id,
            input_summary=input_summary
            or {
                "pair": decision.pair,
                "timeframes": decision.timeframes,
                "chart_statuses": chart_statuses
                or {
                    "4H": decision.analysis_4h.status,
                    "1H": decision.analysis_1h.status,
                    "15M": decision.analysis_15m.status,
                },
            },
            validated_concepts=concepts,
            evidence_summary=evidence_summary or {},
            reasoning_summary=reasoning_summary
            or {
                "explanation": decision.explanation[:500],
                "reasons": decision.reasons[:8],
            },
            decision=bias,
            confidence=decision.confidence,
            knowledge_version=CURRENT_VERSION,
            variant_id=variant_id,
            metadata={"warnings": decision.warnings[:12]},
        )
        return path.log_id

    def record_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        review_scores: dict[str, Any] | None = None,
        lessons_count: int = 0,
    ) -> None:
        self.paths.attach_outcome(trade_id, outcome=outcome, review_scores=review_scores)
        self.counters.incr("learning.pattern_updates")
        if lessons_count:
            self.counters.incr("learning.lessons", lessons_count)
        # Persist a historical evaluation snapshot after each completed outcome.
        try:
            self.build_report(persist=True)
        except Exception:  # noqa: BLE001
            pass

    def record_false_detection(self, *, count: int = 1) -> None:
        """Ground-truth / verification mismatch — never invent structures."""
        self.counters.incr("vision.false_verified", count)

    def record_annotation_compare(self, *, matches: int, mismatches: int) -> None:
        if mismatches:
            self.record_false_detection(count=mismatches)
        if matches:
            self.counters.incr("vision.annotation_matches", matches)

    def build_report(self, *, persist: bool = True) -> EvaluationReport:
        vision = self.metrics.vision()
        features = self.metrics.features()
        knowledge = self.metrics.knowledge()
        evidence = self.metrics.evidence()
        decisions = self.metrics.decisions()
        calibration = self.metrics.calibration()
        reviews = self.metrics.trade_reviews()
        learning = self.metrics.learning()

        report = EvaluationReport(
            report_id=str(uuid.uuid4()),
            created_at=utc_now_iso(),
            vision=vision,
            features=features,
            knowledge=knowledge,
            evidence=evidence,
            decisions=decisions,
            calibration=calibration,
            trade_reviews=reviews,
            learning=learning,
            notes=[
                "Scores are derived from accumulated counters and reviews.",
                "Confidence is never assumed correct — see calibration metrics.",
            ],
        )
        report.health = self.health.build(report)

        if persist:
            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO eval_reports (report_id, created_at, report_json)
                    VALUES (?, ?, ?)
                    """,
                    (report.report_id, report.created_at, report.model_dump_json()),
                )
                conn.commit()
        return report

    def latest_report(self) -> EvaluationReport | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT report_json FROM eval_reports ORDER BY created_at DESC LIMIT 1"
            ).fetchone()
        if row is None:
            return None
        return EvaluationReport.model_validate_json(row["report_json"])

    def list_reports(self, limit: int = 10) -> list[EvaluationReport]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT report_json FROM eval_reports ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [EvaluationReport.model_validate_json(r["report_json"]) for r in rows]


def _parse_rr(value: str | None) -> float | None:
    if not value or value == "—":
        return None
    try:
        return float(str(value).replace(" ", "").split(":")[-1])
    except ValueError:
        return None
