"""Multi-timeframe relationship layer — alignment / conflict / nested structures."""

from __future__ import annotations

from cv.models import MTFRelationship, VisionChartResult


def _trend_label(result: VisionChartResult) -> str:
    for feature in result.features:
        if feature.id == "trend_primary":
            return str(feature.location.get("trend") or feature.label or "Unknown")
    return "Unknown"


def _has(result: VisionChartResult, feature_type: str) -> bool:
    return any(f.type == feature_type and f.confidence > 0 for f in result.features)


class MTFRelationshipAnalyzer:
    def compare(
        self,
        chart_4h: VisionChartResult,
        chart_1h: VisionChartResult,
        chart_15m: VisionChartResult,
    ) -> MTFRelationship:
        if chart_4h.status != "ok" or chart_1h.status != "ok" or chart_15m.status != "ok":
            return MTFRelationship(
                alignment="Unknown",
                notes=["One or more timeframe visions failed — relationship unknown."],
                confidence=0.0,
            )

        t4 = _trend_label(chart_4h)
        t1 = _trend_label(chart_1h)
        t15 = _trend_label(chart_15m)
        notes: list[str] = []
        nested: list[str] = []

        if t4 in {"Bullish", "Bearish"} and t4 == t1 == t15:
            alignment = "Aligned"
            continuation = True
            reversal = False
            notes.append(f"All timeframes agree: {t4}.")
            confidence = 90.0
        elif t4 in {"Bullish", "Bearish"} and t4 == t1 and t15 != t4:
            alignment = "Partial"
            continuation = _has(chart_15m, "pullback") or t15 == "Range"
            reversal = _has(chart_15m, "choch")
            notes.append("4H/1H aligned; 15M diverges (pullback or early shift).")
            confidence = 70.0
        elif t4 in {"Bullish", "Bearish"} and t1 != t4:
            alignment = "Conflict"
            continuation = False
            reversal = _has(chart_1h, "choch") or _has(chart_15m, "choch")
            notes.append(f"Higher-timeframe conflict: 4H={t4}, 1H={t1}.")
            confidence = 75.0
        else:
            alignment = "Unknown"
            continuation = False
            reversal = False
            notes.append("Trend relationship unclear.")
            confidence = 30.0

        if _has(chart_4h, "bos") and _has(chart_1h, "bos"):
            nested.append("1H BOS nested inside 4H BOS context")
        if _has(chart_1h, "liquidity_sweep") and _has(chart_15m, "bos"):
            nested.append("15M BOS after 1H liquidity sweep")
        if _has(chart_4h, "bullish_order_block") and _has(chart_15m, "bullish_fvg"):
            nested.append("15M bullish FVG reacting inside 4H bullish OB context")
        if _has(chart_4h, "bearish_order_block") and _has(chart_15m, "bearish_fvg"):
            nested.append("15M bearish FVG reacting inside 4H bearish OB context")

        return MTFRelationship(
            alignment=alignment,  # type: ignore[arg-type]
            continuation=continuation,
            reversal=reversal,
            nested_structures=nested,
            notes=notes,
            confidence=confidence,
        )
