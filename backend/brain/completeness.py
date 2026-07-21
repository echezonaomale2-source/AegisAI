"""Data completeness checks — missing critical evidence → NO TRADE."""

from __future__ import annotations

from brain.models import CompletenessReport, EngineBundle


CRITICAL_KEYS = (
    "usable_4h",
    "usable_1h",
    "usable_15m",
    "trend_4h",
)


class CompletenessChecker:
    def check(self, bundle: EngineBundle) -> CompletenessReport:
        missing_critical: list[str] = []
        missing_optional: list[str] = []
        notes: list[str] = []
        poor_quality = False

        vision = bundle.vision_summaries
        for tf in ("4H", "1H", "15M"):
            summary = vision.get(tf) or {}
            status = summary.get("status", "error")
            quality = float(summary.get("quality", 0) or 0)
            if status != "ok":
                missing_critical.append(f"{tf}_chart_usable")
                notes.append(f"{tf} chart not usable.")
            if quality and quality < 40:
                poor_quality = True
                notes.append(f"{tf} image quality low ({quality:.0f}%).")

        reasoning = bundle.reasoning or {}
        if not reasoning.get("conclusion"):
            missing_critical.append("reasoning_conclusion")

        if not bundle.validated_concepts and bundle.provisional_bias in {"BUY", "SELL"}:
            missing_optional.append("validated_concepts")

        evidence = bundle.evidence_by_tf or {}
        if not evidence.get("4H"):
            missing_critical.append("evidence_4h")

        # HTF trend required for directional trades
        trend_4h = (vision.get("4H") or {}).get("trend", "Unknown")
        if trend_4h == "Unknown" and bundle.provisional_bias in {"BUY", "SELL"}:
            missing_critical.append("trend_4h")

        request_better = poor_quality or any("chart_usable" in m for m in missing_critical)
        if request_better:
            notes.append("Request a clearer screenshot if image quality is insufficient.")

        complete = len(missing_critical) == 0 and not poor_quality
        return CompletenessReport(
            complete=complete,
            missing_critical=missing_critical,
            missing_optional=missing_optional,
            poor_image_quality=poor_quality,
            request_better_screenshot=request_better,
            notes=notes,
        )
