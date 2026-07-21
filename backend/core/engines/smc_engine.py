"""Smart Money Engine — structured reasoning from ChartModel + FeatureSet (no BUY/SELL)."""

from __future__ import annotations

from core.logging_setup import get_logger
from core.models.analysis import SMCAnalysis
from core.models.chart import ChartModel
from core.models.features import FeatureSet

log = get_logger("smc")


class SmartMoneyEngine:
    def analyze(self, chart: ChartModel, features: FeatureSet) -> SMCAnalysis:
        if not chart.is_usable:
            return SMCAnalysis(
                timeframe=chart.timeframe or "Unknown",
                pair=chart.pair,
                trend="Unknown",
                market_structure="Unknown",
                liquidity="Unknown",
                order_blocks="Unknown",
                fair_value_gaps="Unknown",
                supply_demand="Unknown",
                premium_discount="Unknown",
                confidence=0.0,
                reasoning=["Chart reconstruction failed or incomplete."],
                feature_set=features,
                chart=chart,
                notes=list(chart.notes),
            )

        liquidity = "None Detected"
        if chart.liquidity_zones:
            sweep = next((z for z in chart.liquidity_zones if z.kind == "sweep"), None)
            if sweep:
                liquidity = sweep.label or "Liquidity Sweep"
            else:
                top = max(chart.liquidity_zones, key=lambda z: z.confidence)
                liquidity = top.label or top.kind

        ob_label = "None Detected"
        if any(o.side == "bullish" for o in chart.order_blocks):
            ob_label = "Bullish Order Block"
        elif any(o.side == "bearish" for o in chart.order_blocks):
            ob_label = "Bearish Order Block"

        fvg_label = "None Detected"
        if any(g.side == "bullish" for g in chart.fair_value_gaps):
            fvg_label = "Bullish FVG"
        elif any(g.side == "bearish" for g in chart.fair_value_gaps):
            fvg_label = "Bearish FVG"

        sd = "Balanced"
        if chart.demand_zones and not chart.supply_zones:
            sd = "Demand"
        elif chart.supply_zones and not chart.demand_zones:
            sd = "Supply"

        pd = "Equilibrium"
        if chart.premium == "Yes":
            pd = "Premium"
        elif chart.discount == "Yes":
            pd = "Discount"

        reasoning = [
            f"Trend: {chart.trend.direction} ({chart.trend.confidence:.0f}%)",
            f"Structure: {chart.market_structure_label}",
            f"BOS={'yes' if chart.bos else 'no'} | CHOCH={'yes' if chart.choch else 'no'}",
            f"Liquidity: {liquidity}",
            f"Order blocks: {ob_label}",
            f"FVG: {fvg_label}",
            f"Zones: {sd} | {pd}",
        ]

        confidence = features.overall_confidence or chart.reconstruction_confidence
        log.info(
            "SMC analysis tf=%s trend=%s structure=%s conf=%.1f",
            chart.timeframe,
            chart.trend.direction,
            chart.market_structure_label,
            confidence,
        )

        return SMCAnalysis(
            timeframe=chart.timeframe,
            pair=chart.pair,
            trend=chart.trend.direction,
            market_structure=chart.market_structure_label,
            liquidity=liquidity,
            liquidity_sweep=any(z.kind == "sweep" or z.swept for z in chart.liquidity_zones),
            order_blocks=ob_label,
            fair_value_gaps=fvg_label,
            supply_demand=sd,
            premium_discount=pd,
            bos=chart.bos,
            choch=chart.choch,
            confidence=confidence,
            reasoning=reasoning,
            feature_set=features,
            chart=chart,
            notes=list(chart.notes),
        )
