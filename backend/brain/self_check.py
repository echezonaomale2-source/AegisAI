"""Brain self-check — final gate before recommendation."""

from __future__ import annotations

from brain.models import (
    BrainSelfCheck,
    CompletenessReport,
    ConflictReport,
    EngineBundle,
    HistoricalSupport,
)


class BrainSelfChecker:
    MIN_CONFIDENCE = 70.0

    def check(
        self,
        bundle: EngineBundle,
        *,
        completeness: CompletenessReport,
        conflicts: ConflictReport,
        historical: HistoricalSupport,
        confidence: float,
        candidate: str,
    ) -> BrainSelfCheck:
        warnings: list[str] = []

        evidence_complete = completeness.complete and not completeness.missing_critical
        if not evidence_complete:
            warnings.append("Evidence incomplete — critical inputs missing.")

        evidence_consistent = not (
            conflicts.htf_disagreement or conflicts.severity == "high"
        )
        if not evidence_consistent:
            warnings.append("Evidence internally inconsistent — HTF conflict or high severity.")

        confidence_justified = confidence >= self.MIN_CONFIDENCE or candidate == "NO TRADE"
        if candidate in {"BUY", "SELL"} and confidence < self.MIN_CONFIDENCE:
            warnings.append(f"Confidence {confidence:.0f}% not justified (need ≥ {self.MIN_CONFIDENCE:.0f}%).")

        risk = bundle.risk or {}
        risk_ok = bool(risk.get("valid", True)) if candidate in {"BUY", "SELL"} else True

        professional = (
            evidence_complete
            and evidence_consistent
            and confidence_justified
            and risk_ok
        )
        if (
            candidate in {"BUY", "SELL"}
            and historical.historical_support == "Weak"
            and historical.previous_similar_analyses >= 10
        ):
            warnings.append("Historical support weak — a professional trader may pass.")
            professional = False

        prefer_no_trade = False
        if candidate in {"BUY", "SELL"}:
            if not evidence_complete or not evidence_consistent:
                prefer_no_trade = True
            if not confidence_justified:
                prefer_no_trade = True
            if conflicts.htf_disagreement:
                prefer_no_trade = True
                warnings.append("Higher timeframes disagree — NO TRADE is safer.")
            if completeness.request_better_screenshot:
                prefer_no_trade = True
                warnings.append("Poor image quality — request a better screenshot.")
            if not risk_ok:
                prefer_no_trade = True
                warnings.append("Risk plan invalid — NO TRADE safer.")
            if (
                historical.historical_support == "Weak"
                and historical.previous_similar_analyses >= 20
                and historical.wins + historical.losses >= 10
            ):
                prefer_no_trade = True
                warnings.append("Consistently weak historical outcomes — NO TRADE safer.")

        passed = (
            candidate == "NO TRADE"
            or (evidence_complete and evidence_consistent and confidence_justified and not prefer_no_trade)
        )

        return BrainSelfCheck(
            evidence_complete=evidence_complete,
            evidence_consistent=evidence_consistent,
            confidence_justified=confidence_justified,
            professional_setup=professional if candidate in {"BUY", "SELL"} else True,
            prefer_no_trade=prefer_no_trade,
            passed=passed,
            warnings=warnings,
        )
