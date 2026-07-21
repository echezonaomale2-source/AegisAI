"""Engine 6 — Decision Engine: ReasoningReport + Risk → CognitiveDecision."""

from __future__ import annotations

import hashlib
import json

from cognitive.events import EVT_DECISION_MADE, EventBus
from cognitive.models.decision import CognitiveDecision, TradeGrade
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from cognitive.weights import MIN_CONFIDENCE
from core.logging_setup import get_logger

log = get_logger("cognitive.decision")

_PLACEHOLDER_LEVELS = {"", "—", "-", "n/a", "na", "none", "unknown"}


class CognitiveDecisionEngine:
    """
    Generate final recommendation with entry/SL/TP, grade, and explanation.

    Always NO TRADE when evidence or risk is insufficient — never guess.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    def decide(
        self,
        report: ReasoningReport,
        risk: RiskAssessment,
        *,
        pair: str = "Unknown",
    ) -> CognitiveDecision:
        recommendation = report.conclusion
        confidence = report.confidence
        warnings: list[str] = []
        reasons: list[str] = list(report.narrative)
        gates_applied: list[str] = list(report.gates_failed)

        # Surface reasoning gates as warnings
        for gate in report.gates_failed:
            warnings.append(f"Reasoning gate: {gate}")

        # Risk gate
        if recommendation in {"BUY", "SELL"}:
            confidence = max(0.0, min(100.0, confidence + risk.confidence_adjustment))
            if not risk.valid:
                warnings.append("Risk plan invalid or RR below 1.5 — forcing NO TRADE.")
                recommendation = "NO TRADE"
                reasons.append("Risk Engine rejected the setup.")
                gates_applied.append("risk_invalid")
            elif confidence < MIN_CONFIDENCE:
                warnings.append(
                    f"Post-risk confidence {confidence:.0f}% below {MIN_CONFIDENCE:.0f}%."
                )
                recommendation = "NO TRADE"
                reasons.append("Confidence after risk adjustment is insufficient.")
                gates_applied.append("post_risk_confidence")
            elif not self._levels_complete(risk):
                warnings.append(
                    "Entry / stop / take-profit incomplete — forcing NO TRADE (never invent levels)."
                )
                recommendation = "NO TRADE"
                reasons.append("Risk levels incomplete.")
                gates_applied.append("incomplete_levels")

        if recommendation == "NO TRADE":
            entry = stop = take = rr = "—"
            grade: TradeGrade = "F"
            explanation = self._explain_no_trade(report, risk, reasons, warnings, gates_applied)
        else:
            entry, stop, take, rr = risk.entry, risk.stop_loss, risk.take_profit, risk.risk_reward
            grade = self._trade_grade(confidence, risk.risk_grade, report)
            explanation = self._explain_trade(
                recommendation, report, risk, grade, reasons, confidence
            )

        # Attach supporting evidence as reasons
        for item in report.supporting[:6]:
            reasons.append(f"Support: {item.rationale}")
        for item in report.conflicting[:4]:
            warnings.append(f"Conflict: {item.rationale}")
        for s in report.supporting_structures[:4]:
            reasons.append(f"Structure support: {s}")
        for s in report.conflicting_structures[:4]:
            warnings.append(f"Structure conflict: {s}")

        payload = {
            "pair": pair or report.pair,
            "recommendation": recommendation,
            "confidence": round(confidence, 1),
            "trace": report.trace,
            "buy": report.buy_evidence_score,
            "sell": report.sell_evidence_score,
            "risk_grade": risk.risk_grade,
            "gates": gates_applied,
        }
        repro = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

        decision = CognitiveDecision(
            pair=pair or report.pair,
            recommendation=recommendation,  # type: ignore[arg-type]
            entry=entry,
            stop_loss=stop,
            take_profit=take,
            risk_reward=rr,
            confidence=round(confidence, 1),
            trade_grade=grade,
            explanation=explanation,
            reasons=reasons,
            warnings=warnings,
            gates_applied=gates_applied,
            reasoning=report,
            risk=risk,
            reproducible_hash=repro,
        )
        log.info(
            "decision %s grade=%s conf=%.1f hash=%s gates=%s",
            recommendation,
            grade,
            confidence,
            repro,
            gates_applied or ["none"],
        )
        if self._bus:
            self._bus.publish(
                EVT_DECISION_MADE,
                {
                    "recommendation": recommendation,
                    "grade": grade,
                    "confidence": confidence,
                    "hash": repro,
                },
            )
        return decision

    @staticmethod
    def _levels_complete(risk: RiskAssessment) -> bool:
        for value in (risk.entry, risk.stop_loss, risk.take_profit, risk.risk_reward):
            if str(value).strip().lower() in _PLACEHOLDER_LEVELS:
                return False
        return True

    def _trade_grade(
        self,
        confidence: float,
        risk_grade: str,
        report: ReasoningReport,
    ) -> TradeGrade:
        margin = abs(report.buy_evidence_score - report.sell_evidence_score)
        if confidence >= 90 and risk_grade == "A" and margin >= 25:
            return "A+"
        if confidence >= 85 and risk_grade in {"A", "B"}:
            return "A"
        if confidence >= 78 and risk_grade in {"A", "B", "C"}:
            return "B"
        if confidence >= 70:
            return "C"
        if confidence >= 55:
            return "D"
        return "F"

    def _explain_no_trade(
        self,
        report: ReasoningReport,
        risk: RiskAssessment,
        reasons: list[str],
        warnings: list[str],
        gates: list[str],
    ) -> str:
        parts = [
            "NO TRADE — insufficient or conflicting evidence for a professional entry.",
            f"BUY evidence {report.buy_evidence_score:.0f} | "
            f"SELL evidence {report.sell_evidence_score:.0f} | "
            f"Neutral {report.neutral_score:.0f}.",
            f"Traceable confidence {report.confidence:.0f}% "
            f"(uncertainty {report.image_uncertainty:.0f}%).",
            f"Trade grade F | Entry — | SL — | TP — | RR —.",
        ]
        if gates:
            parts.append("Gates: " + ", ".join(gates))
        if report.conflicts_summary:
            parts.append("Conflicts: " + "; ".join(report.conflicts_summary[:3]))
        if report.missing:
            parts.append("Missing structures (not invented): " + ", ".join(report.missing[:5]))
        if risk.notes:
            parts.append(risk.notes[0])
        parts.extend(reasons[:3])
        parts.extend(warnings[:2])
        return " ".join(parts)

    def _explain_trade(
        self,
        side: str,
        report: ReasoningReport,
        risk: RiskAssessment,
        grade: str,
        reasons: list[str],
        confidence: float,
    ) -> str:
        top = ", ".join(i.name for i in report.supporting[:4]) or "aggregated evidence"
        return (
            f"{side} grade {grade} at {confidence:.0f}% confidence. "
            f"Evidence: BUY {report.buy_evidence_score:.0f} vs SELL {report.sell_evidence_score:.0f}. "
            f"Key support: {top}. "
            f"Entry {risk.entry} | SL {risk.stop_loss} | TP {risk.take_profit} | RR {risk.risk_reward}. "
            f"Risk grade {risk.risk_grade}. "
            f"Explanation trail: {report.explanation or '; '.join(report.narrative[:3])}."
        )
