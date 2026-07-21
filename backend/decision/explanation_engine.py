"""Explanation engine — discretionary-style trade narrative (never vague)."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, RiskPlan, TradeDirection


class ExplanationEngine:
    def build(
        self,
        *,
        direction: TradeDirection,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        scorecard: ConfidenceScorecard,
        risk: RiskPlan,
        no_trade_reasons: list[str],
    ) -> tuple[str, list[str]]:
        reasons: list[str] = []

        if direction == "NO TRADE":
            reasons.extend(no_trade_reasons or ["Evidence insufficient for a professional setup."])
            explanation = (
                "NO TRADE\n\n"
                + "\n".join(f"- {r}" for r in reasons)
                + f"\n\nConfidence score: {scorecard.overall:.0f}% "
                f"(minimum required: professional threshold not met or rules blocked the trade)."
            )
            return explanation, reasons

        if direction == "BUY":
            reasons.append("4H trend is bullish.")
            if h4.bos:
                reasons.append("4H shows bullish break of structure.")
            if h4.demand_zone or h4.discount == "Yes":
                reasons.append("4H price location favors demand / discount.")
            reasons.append("1H aligns with the higher-timeframe bullish bias.")
            if h1.liquidity_sweep:
                reasons.append("1H liquidity sweep detected into discount/demand.")
            if h1.bullish_order_block:
                reasons.append("1H bullish order block is present.")
            if h1.fair_value_gap and h1.fvg_type == "Bullish FVG":
                reasons.append("1H bullish fair value gap supports continuation.")
            if m15.liquidity_sweep:
                reasons.append("15M liquidity sweep provided entry conditions.")
            if m15.choch:
                reasons.append("15M change of character confirmed bullish shift.")
            if m15.bos:
                reasons.append("15M bullish BOS confirmed.")
            if m15.bullish_order_block:
                reasons.append("15M bullish order block respected / mitigated into.")
            if m15.fair_value_gap and m15.fvg_type == "Bullish FVG":
                reasons.append("15M fair value gap fill / reaction observed.")
            if m15.strong_rejection:
                reasons.append("15M strong rejection candle supports entry.")
            reasons.append("15M produced bullish confirmation.")
            reasons.append("High-probability continuation only while HTF alignment holds.")
        else:
            reasons.append("4H trend is bearish.")
            if h4.bos:
                reasons.append("4H shows bearish break of structure.")
            if h4.supply_zone or h4.premium == "Yes":
                reasons.append("4H price location favors supply / premium.")
            reasons.append("1H aligns with the higher-timeframe bearish bias.")
            if h1.liquidity_sweep:
                reasons.append("1H liquidity sweep detected into premium/supply.")
            if h1.bearish_order_block:
                reasons.append("1H bearish order block is present.")
            if h1.fair_value_gap and h1.fvg_type == "Bearish FVG":
                reasons.append("1H bearish fair value gap supports continuation.")
            if m15.liquidity_sweep:
                reasons.append("15M liquidity sweep provided entry conditions.")
            if m15.choch:
                reasons.append("15M change of character confirmed bearish shift.")
            if m15.bos:
                reasons.append("15M bearish BOS confirmed.")
            if m15.bearish_order_block:
                reasons.append("15M bearish order block respected / mitigated into.")
            if m15.fair_value_gap and m15.fvg_type == "Bearish FVG":
                reasons.append("15M fair value gap fill / reaction observed.")
            if m15.strong_rejection:
                reasons.append("15M strong rejection candle supports entry.")
            reasons.append("15M produced bearish confirmation.")
            reasons.append("High-probability continuation only while HTF alignment holds.")

        explanation = (
            f"{direction}\n\n"
            + "\n".join(f"- {r}" for r in reasons)
            + "\n\nSetup\n"
            + f"- Entry: {risk.entry}\n"
            + f"- Stop Loss: {risk.stop_loss}\n"
            + f"- Take Profit: {risk.take_profit}\n"
            + f"- Risk Reward: {risk.risk_reward}\n"
            + f"- Target Liquidity: {risk.target_liquidity}\n"
            + f"\nConfidence: {scorecard.overall:.0f}% "
            + f"(4H {scorecard.htf_4h_alignment:.0f} · "
            + f"1H {scorecard.mtf_1h_alignment:.0f} · "
            + f"15M {scorecard.ltf_15m_confirmation:.0f})"
        )
        return explanation, reasons
