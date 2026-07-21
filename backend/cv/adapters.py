"""Map Phase 5 VisionChartResult → Phase 2 ChartAnalysis (API compatibility)."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis, PriceContext
from services.output_formatter import build_confidence_breakdown
from cv.models import VisionChartResult


def vision_to_chart_analysis(result: VisionChartResult) -> ChartAnalysis:
    if result.status != "ok":
        return ChartAnalysis(
            status="error",
            error=result.error or "Image Quality Too Low",
            pair=result.meta.pair or "Unknown",
            timeframe=result.meta.timeframe or "Unknown",
            detected_timeframe_label=result.meta.detected_timeframe_label,
            trend="Unknown",
            market_structure="Unknown",
            session_labels=list(result.meta.session_labels),
            candle_count=len(result.candles),
            confidence=0.0,
            notes=result.notes or [result.error or "Image Quality Too Low"],
        )

    summary = result.summary or {}
    trend_raw = summary.get("trend", "Unknown")
    trend = trend_raw if trend_raw in {"Bullish", "Bearish", "Range"} else "Unknown"

    structure_label = "Unknown"
    for feature in result.features:
        if feature.id == "structure_primary" and feature.label:
            structure_label = feature.label
            break

    def conf(ftype: str, default: float = 0.0) -> float:
        for feature in result.features:
            if feature.type == ftype and feature.confidence > 0:
                return feature.confidence
        return default

    bos = bool(summary.get("bos"))
    choch = bool(summary.get("choch"))
    liquidity_sweep = bool(summary.get("liquidity_sweep"))
    bullish_ob = bool(summary.get("bullish_order_block"))
    bearish_ob = bool(summary.get("bearish_order_block"))
    bullish_fvg = bool(summary.get("bullish_fvg"))
    bearish_fvg = bool(summary.get("bearish_fvg"))

    liquidity_label = "None Detected"
    for feature in result.features:
        if feature.type == "liquidity_sweep":
            liquidity_label = "Liquidity Sweep"
            break
        if feature.type == "equal_highs":
            liquidity_label = "Equal Highs"
        elif feature.type == "equal_lows":
            liquidity_label = "Equal Lows"
        elif feature.type == "liquidity" and feature.label:
            liquidity_label = feature.label

    fvg_type = None
    if bullish_fvg:
        fvg_type = "Bullish FVG"
    elif bearish_fvg:
        fvg_type = "Bearish FVG"

    premium = "Unknown"
    discount = "Unknown"
    supply = any(f.type == "supply_zone" for f in result.features)
    demand = any(f.type == "demand_zone" for f in result.features)
    if any(f.type == "premium" for f in result.features):
        premium, discount = "Yes", "No"
    elif any(f.type == "discount" for f in result.features):
        premium, discount = "No", "Yes"

    strong_rej = any(f.type == "rejection" and f.label == "Strong Rejection" for f in result.features)
    weak_rej = any(f.type == "rejection" and f.label == "Weak Rejection" for f in result.features)
    impulse = any(f.type == "impulse" for f in result.features)
    pullback = any(f.type == "pullback" for f in result.features)

    candles = result.candles
    price_context = None
    if candles:
        highs = [c.high for c in candles]
        lows = [c.low for c in candles]
        price_context = PriceContext(
            last_close=candles[-1].close,
            last_high=candles[-1].high,
            last_low=candles[-1].low,
            swing_high=max(highs),
            swing_low=min(lows),
            range_high=max(highs),
            range_low=min(lows),
            avg_range=sum(c.high - c.low for c in candles) / len(candles),
        )

    conf_parts = {
        "trend": conf("trend", conf("range", 40.0)),
        "market_structure": conf("higher_high", conf("lower_low", conf("higher_low", conf("lower_high", 40.0)))),
        "bos": conf("bos", 20.0 if not bos else 80.0),
        "choch": conf("choch", 20.0 if not choch else 80.0),
        "liquidity": conf("liquidity", conf("liquidity_sweep", 35.0)),
        "liquidity_sweep": conf("liquidity_sweep", 25.0),
        "order_block": conf("bullish_order_block", conf("bearish_order_block", 25.0)),
        "fair_value_gap": conf("bullish_fvg", conf("bearish_fvg", 25.0)),
        "zones": conf("demand_zone", conf("supply_zone", 40.0)),
    }
    breakdown = build_confidence_breakdown(conf_parts)

    swing_highs = sum(1 for f in result.features if f.type == "swing_high")
    swing_lows = sum(1 for f in result.features if f.type == "swing_low")

    return ChartAnalysis(
        status="ok",
        pair=result.meta.pair,
        timeframe=result.meta.timeframe,
        detected_timeframe_label=result.meta.detected_timeframe_label,
        trend=trend,  # type: ignore[arg-type]
        market_structure=structure_label,
        bos=bos,
        choch=choch,
        liquidity=liquidity_label,
        liquidity_sweep=liquidity_sweep,
        equal_highs=any(f.type == "equal_highs" for f in result.features),
        equal_lows=any(f.type == "equal_lows" for f in result.features),
        internal_liquidity=swing_highs + swing_lows >= 4,
        external_liquidity=swing_highs > 0 and swing_lows > 0,
        bullish_order_block=bullish_ob,
        bearish_order_block=bearish_ob,
        fair_value_gap=bullish_fvg or bearish_fvg,
        fvg_type=fvg_type,
        supply_zone=supply,
        demand_zone=demand,
        premium=premium,  # type: ignore[arg-type]
        discount=discount,  # type: ignore[arg-type]
        strong_rejection=strong_rej,
        weak_rejection=weak_rej,
        impulse_move=impulse,
        correction_move=pullback,
        session_labels=list(result.meta.session_labels),
        candle_count=len(candles),
        swing_high_count=swing_highs,
        swing_low_count=swing_lows,
        price_context=price_context,
        confidence=breakdown.overall,
        confidence_breakdown=breakdown,
        notes=result.notes,
    )
