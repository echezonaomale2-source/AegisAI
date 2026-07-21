"""Format and confidence aggregation for chart analysis output."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis, ConfidenceBreakdown


def build_confidence_breakdown(parts: dict[str, float]) -> ConfidenceBreakdown:
    trend = parts.get("trend", 0.0)
    market_structure = parts.get("market_structure", 0.0)
    bos = parts.get("bos", 0.0)
    choch = parts.get("choch", 0.0)
    liquidity = parts.get("liquidity", 0.0)
    liquidity_sweep = parts.get("liquidity_sweep", 0.0)
    order_block = parts.get("order_block", 0.0)
    fair_value_gap = parts.get("fair_value_gap", 0.0)
    zones = parts.get("zones", 0.0)

    weighted = [
        (trend, 1.2),
        (market_structure, 1.2),
        (bos, 1.0),
        (choch, 1.0),
        (liquidity, 1.0),
        (liquidity_sweep, 0.9),
        (order_block, 1.0),
        (fair_value_gap, 0.9),
        (zones, 0.8),
    ]
    total_w = sum(w for _, w in weighted)
    overall = sum(v * w for v, w in weighted) / total_w if total_w else 0.0

    return ConfidenceBreakdown(
        trend=round(trend, 1),
        market_structure=round(market_structure, 1),
        bos=round(bos, 1),
        choch=round(choch, 1),
        liquidity=round(liquidity, 1),
        liquidity_sweep=round(liquidity_sweep, 1),
        order_block=round(order_block, 1),
        fair_value_gap=round(fair_value_gap, 1),
        zones=round(zones, 1),
        overall=round(overall, 1),
    )


def quality_error_result(message: str = "Image Quality Too Low") -> ChartAnalysis:
    return ChartAnalysis(
        status="error",
        error=message,
        pair="Unknown",
        timeframe="Unknown",
        trend="Unknown",
        market_structure="Unknown",
        confidence=0.0,
        notes=[message],
    )
