"""Adapters: ChartModel / TradeAnalysis ↔ legacy ChartAnalysis / DecisionEngine."""

from __future__ import annotations

from core.models.analysis import SMCAnalysis, TradeAnalysis
from core.models.chart import ChartModel
from models.chart_schemas import ChartAnalysis, MultiChartAnalysis, PriceContext
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from services.output_formatter import build_confidence_breakdown


def chart_model_to_chart_analysis(chart: ChartModel) -> ChartAnalysis:
    """Compatibility bridge for Phase 3 DecisionEngine (unchanged contract)."""
    if not chart.is_usable:
        return ChartAnalysis(
            status="error",
            error=chart.error or "Image Quality Too Low",
            pair=chart.pair,
            timeframe=chart.timeframe,
            detected_timeframe_label=chart.detected_timeframe_label,
            trend="Unknown",
            market_structure="Unknown",
            session_labels=list(chart.session_labels),
            candle_count=len(chart.candles),
            confidence=0.0,
            notes=list(chart.notes),
        )

    price_context = None
    if chart.candles:
        highs = [c.high for c in chart.candles]
        lows = [c.low for c in chart.candles]
        price_context = PriceContext(
            last_close=chart.candles[-1].close,
            last_high=chart.candles[-1].high,
            last_low=chart.candles[-1].low,
            swing_high=max(highs),
            swing_low=min(lows),
            range_high=max(highs),
            range_low=min(lows),
            avg_range=sum(c.high - c.low for c in chart.candles) / len(chart.candles),
        )

    bullish_ob = any(o.side == "bullish" for o in chart.order_blocks)
    bearish_ob = any(o.side == "bearish" for o in chart.order_blocks)
    bullish_fvg = any(g.side == "bullish" for g in chart.fair_value_gaps)
    bearish_fvg = any(g.side == "bearish" for g in chart.fair_value_gaps)

    liquidity_label = "None Detected"
    if chart.liquidity_zones:
        sweep = next((z for z in chart.liquidity_zones if z.kind == "sweep" or z.swept), None)
        if sweep:
            liquidity_label = sweep.label or "Liquidity Sweep"
        else:
            top = max(chart.liquidity_zones, key=lambda z: z.confidence)
            liquidity_label = top.label or top.kind.replace("_", " ").title()

    fvg_type = None
    if bullish_fvg:
        fvg_type = "Bullish FVG"
    elif bearish_fvg:
        fvg_type = "Bearish FVG"

    swing_highs = sum(1 for s in chart.swing_points if s.kind == "high")
    swing_lows = sum(1 for s in chart.swing_points if s.kind == "low")

    conf_parts = {
        "trend": chart.trend.confidence or 40.0,
        "market_structure": 70.0 if chart.market_structure_label != "Unknown" else 40.0,
        "bos": 80.0 if chart.bos else 20.0,
        "choch": 80.0 if chart.choch else 20.0,
        "liquidity": max((z.confidence for z in chart.liquidity_zones), default=35.0),
        "liquidity_sweep": 80.0 if any(z.kind == "sweep" or z.swept for z in chart.liquidity_zones) else 25.0,
        "order_block": max((o.confidence for o in chart.order_blocks), default=25.0),
        "fair_value_gap": max((g.confidence for g in chart.fair_value_gaps), default=25.0),
        "zones": max(
            [z.confidence for z in chart.supply_zones + chart.demand_zones] or [40.0]
        ),
    }
    breakdown = build_confidence_breakdown(conf_parts)

    return ChartAnalysis(
        status="ok",
        pair=chart.pair,
        timeframe=chart.timeframe,
        detected_timeframe_label=chart.detected_timeframe_label,
        trend=chart.trend.direction,  # type: ignore[arg-type]
        market_structure=chart.market_structure_label,
        bos=chart.bos,
        choch=chart.choch,
        liquidity=liquidity_label,
        liquidity_sweep=any(z.kind == "sweep" or z.swept for z in chart.liquidity_zones),
        equal_highs=any(z.kind == "equal_highs" for z in chart.liquidity_zones),
        equal_lows=any(z.kind == "equal_lows" for z in chart.liquidity_zones),
        internal_liquidity=swing_highs + swing_lows >= 4,
        external_liquidity=swing_highs > 0 and swing_lows > 0,
        bullish_order_block=bullish_ob,
        bearish_order_block=bearish_ob,
        fair_value_gap=bullish_fvg or bearish_fvg,
        fvg_type=fvg_type,
        supply_zone=bool(chart.supply_zones),
        demand_zone=bool(chart.demand_zones),
        premium=chart.premium,
        discount=chart.discount,
        strong_rejection=chart.strong_rejection,
        weak_rejection=chart.weak_rejection,
        impulse_move=chart.trend.impulse_move,
        correction_move=chart.trend.pullback,
        session_labels=list(chart.session_labels),
        candle_count=len(chart.candles),
        swing_high_count=swing_highs,
        swing_low_count=swing_lows,
        price_context=price_context,
        confidence=breakdown.overall,
        confidence_breakdown=breakdown,
        notes=list(chart.notes),
    )


def smc_to_chart_analysis(smc: SMCAnalysis) -> ChartAnalysis:
    if smc.chart is not None:
        return chart_model_to_chart_analysis(smc.chart)
    return ChartAnalysis(
        status="error" if smc.trend == "Unknown" and smc.confidence == 0 else "ok",
        pair=smc.pair,
        timeframe=smc.timeframe,
        trend=smc.trend,  # type: ignore[arg-type]
        market_structure=smc.market_structure,
        bos=smc.bos,
        choch=smc.choch,
        liquidity=smc.liquidity,
        liquidity_sweep=smc.liquidity_sweep,
        bullish_order_block=smc.order_blocks == "Bullish Order Block",
        bearish_order_block=smc.order_blocks == "Bearish Order Block",
        fair_value_gap=smc.fair_value_gaps not in {"None Detected", "Unknown"},
        fvg_type=smc.fair_value_gaps if "FVG" in smc.fair_value_gaps else None,
        supply_zone=smc.supply_demand == "Supply",
        demand_zone=smc.supply_demand == "Demand",
        premium="Yes" if smc.premium_discount == "Premium" else "No" if smc.premium_discount == "Discount" else "Unknown",
        discount="Yes" if smc.premium_discount == "Discount" else "No" if smc.premium_discount == "Premium" else "Unknown",
        confidence=smc.confidence,
        notes=list(smc.notes) + list(smc.reasoning),
    )


def trade_analysis_to_multi(analysis: TradeAnalysis) -> MultiChartAnalysis:
    return MultiChartAnalysis(
        chart_4h=smc_to_chart_analysis(analysis.analysis_4h),
        chart_1h=smc_to_chart_analysis(analysis.analysis_1h),
        chart_15m=smc_to_chart_analysis(analysis.analysis_15m),
    )


class LegacyDecisionAdapter:
    """Wraps Phase 3 DecisionEngine behind DecisionEngineProtocol."""

    def __init__(self) -> None:
        from decision.decision_engine import DecisionEngine

        self._engine = DecisionEngine()

    def decide(self, analysis: TradeAnalysis, *, pair_hint: str | None = None) -> TradeDecision:
        multi = trade_analysis_to_multi(analysis)
        return self._engine.decide(multi, pair_hint=pair_hint)


class LegacyConfidenceAdapter:
    """Wraps Phase 3 ConfidenceEngine; enriches with image quality + historical match."""

    def __init__(self) -> None:
        from decision.confidence_engine import ConfidenceEngine

        self._engine = ConfidenceEngine()

    def score(
        self,
        analysis: TradeAnalysis,
        decision: TradeDecision,
        *,
        image_quality: dict[str, float] | None = None,
        historical_match: float | None = None,
    ) -> ConfidenceScorecard:
        direction = None if decision.overall_bias == "NO TRADE" else decision.overall_bias
        expected = None
        if direction == "BUY":
            expected = "Bullish"
        elif direction == "SELL":
            expected = "Bearish"

        a4 = smc_to_chart_analysis(analysis.analysis_4h)
        a1 = smc_to_chart_analysis(analysis.analysis_1h)
        a15 = smc_to_chart_analysis(analysis.analysis_15m)
        card = self._engine.score(
            h4=a4,
            h1=a1,
            m15=a15,
            candidate_direction=direction,
        )

        # Blend image quality (avg of TFs) and historical pattern match into overall.
        overall = card.overall
        if image_quality:
            iq = sum(image_quality.values()) / max(1, len(image_quality))
            overall = 0.85 * overall + 0.15 * iq
        if historical_match is not None:
            overall = 0.90 * overall + 0.10 * historical_match
        # expected trend used only for documentation of blend path
        _ = expected

        return card.model_copy(update={"overall": max(0.0, min(100.0, overall))})
