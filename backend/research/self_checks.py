"""
Self-checks — run before issuing a recommendation.

Ask: evidence sufficient? conflicts? prefer NO TRADE? pattern consistent? confidence justified?
"""

from __future__ import annotations

from cognitive.models.decision import CognitiveDecision
from cognitive.models.reasoning import ReasoningReport
from models.decision_schemas import TradeDecision
from research.confidence_calibration import ConfidenceCalibrationEngine
from research.models import SelfCheckResult
from research.pattern_library import PatternLibrary


class SelfCheckEngine:
    MIN_EVIDENCE_MARGIN = 12.0
    MIN_CONFIDENCE = 70.0
    MIN_PATTERN_TRADES = 15
    MAX_PATTERN_LOSS_RATE = 0.65

    def __init__(
        self,
        calibration: ConfidenceCalibrationEngine | None = None,
        patterns: PatternLibrary | None = None,
    ) -> None:
        self.calibration = calibration or ConfidenceCalibrationEngine()
        self.patterns = patterns or PatternLibrary()

    def check(
        self,
        decision: TradeDecision | CognitiveDecision,
        *,
        reasoning: ReasoningReport | None = None,
        feature_keys: list[str] | None = None,
    ) -> SelfCheckResult:
        if isinstance(decision, CognitiveDecision):
            bias = decision.recommendation
            confidence = decision.confidence
            warnings_in = list(decision.warnings)
        else:
            bias = decision.overall_bias
            confidence = decision.confidence
            warnings_in = list(decision.warnings)

        checks: list[dict] = []
        warnings: list[str] = []
        force_no_trade = False

        # 1. Evidence sufficiency
        if reasoning is not None:
            margin = abs(reasoning.buy_evidence_score - reasoning.sell_evidence_score)
            sufficient = (
                reasoning.conclusion != "NO TRADE"
                or bias == "NO TRADE"
            )
            evidence_ok = True
            if bias in {"BUY", "SELL"}:
                evidence_ok = (
                    max(reasoning.buy_evidence_score, reasoning.sell_evidence_score) >= 55
                    and margin >= self.MIN_EVIDENCE_MARGIN
                    and len(reasoning.missing) < 4
                )
                if len(reasoning.missing) >= 4:
                    evidence_ok = False
                    warnings.append("Too many missing structures — evidence insufficient.")
                if margin < self.MIN_EVIDENCE_MARGIN:
                    evidence_ok = False
                    warnings.append(f"Evidence margin {margin:.0f} too thin.")
            checks.append(
                {
                    "name": "evidence_sufficient",
                    "passed": evidence_ok if bias in {"BUY", "SELL"} else True,
                    "detail": f"margin={margin:.1f} missing={len(reasoning.missing)}",
                }
            )
            if bias in {"BUY", "SELL"} and not evidence_ok:
                force_no_trade = True
        else:
            checks.append({"name": "evidence_sufficient", "passed": True, "detail": "no reasoning attached"})

        # 2. Conflicting evidence
        if reasoning is not None and bias in {"BUY", "SELL"}:
            conflict_heavy = len(reasoning.conflicting) >= 4 or (
                reasoning.conflicts_summary and len(reasoning.conflicts_summary) >= 3
            )
            checks.append(
                {
                    "name": "conflicts_manageable",
                    "passed": not conflict_heavy,
                    "detail": f"conflicts={len(reasoning.conflicting)}",
                }
            )
            if conflict_heavy:
                force_no_trade = True
                warnings.append("Conflicting evidence suggests NO TRADE is more appropriate.")
        else:
            checks.append({"name": "conflicts_manageable", "passed": True, "detail": "n/a"})

        # 3. Would NO TRADE be more appropriate?
        prefer_no_trade = force_no_trade or (
            bias in {"BUY", "SELL"} and confidence < self.MIN_CONFIDENCE
        )
        checks.append(
            {
                "name": "no_trade_preference",
                "passed": not prefer_no_trade,
                "detail": "prefer NO TRADE" if prefer_no_trade else "trade may proceed",
            }
        )
        if prefer_no_trade and bias in {"BUY", "SELL"}:
            force_no_trade = True
            warnings.append("Self-check: NO TRADE is more appropriate than forcing an entry.")

        # 4. Pattern consistency
        pattern_ok = True
        if feature_keys and bias in {"BUY", "SELL"}:
            record = self.patterns.get(feature_keys)
            if record and record.occurrences >= self.MIN_PATTERN_TRADES:
                closed = record.wins + record.losses
                if closed > 0:
                    loss_rate = record.losses / closed
                    if loss_rate >= self.MAX_PATTERN_LOSS_RATE:
                        pattern_ok = False
                        force_no_trade = True
                        warnings.append(
                            f"Pattern historically unreliable "
                            f"({record.losses}/{closed} losses) — prefer NO TRADE."
                        )
            checks.append(
                {
                    "name": "pattern_consistent",
                    "passed": pattern_ok,
                    "detail": record.pattern_id if record else "insufficient history",
                }
            )
        else:
            checks.append({"name": "pattern_consistent", "passed": True, "detail": "skipped"})

        # 5. Confidence justified vs calibration
        calibrated = self.calibration.adjust(confidence)
        gap = abs(confidence - calibrated)
        conf_ok = gap < 20 or bias == "NO TRADE"
        if bias in {"BUY", "SELL"} and calibrated < self.MIN_CONFIDENCE:
            conf_ok = False
            force_no_trade = True
            warnings.append(
                f"Calibrated confidence {calibrated:.0f}% below threshold "
                f"(raw {confidence:.0f}%)."
            )
        checks.append(
            {
                "name": "confidence_justified",
                "passed": conf_ok,
                "detail": f"raw={confidence:.1f} calibrated={calibrated:.1f}",
            }
        )

        warnings.extend(warnings_in)
        passed = all(c["passed"] for c in checks) and not force_no_trade
        summary = (
            "Self-checks passed."
            if passed
            else "Self-checks recommend withholding or revising the trade."
        )
        return SelfCheckResult(
            passed=passed,
            force_no_trade=force_no_trade and bias in {"BUY", "SELL"},
            checks=checks,
            warnings=list(dict.fromkeys(warnings)),
            summary=summary,
        )
