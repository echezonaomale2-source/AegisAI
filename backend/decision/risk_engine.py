"""Risk engine — entry, stop loss, take profit, RR from chart geometry."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis, PriceContext
from models.decision_schemas import RiskPlan, TradeDirection


def _fmt(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


def _ctx(analysis: ChartAnalysis) -> PriceContext | None:
    return analysis.price_context


class RiskEngine:
    """
    Builds a risk plan from 15M geometry, refined by HTF liquidity targets.

    Prices are chart-relative (vision 0–100 scale) when axis OCR is unavailable.
    """

    def build(
        self,
        *,
        direction: TradeDirection,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
    ) -> RiskPlan:
        if direction == "NO TRADE":
            return RiskPlan(
                trade_direction="NO TRADE",
                notes=["No risk plan — decision is NO TRADE."],
            )

        ctx = _ctx(m15) or _ctx(h1) or _ctx(h4)
        if ctx is None or ctx.last_close is None:
            return RiskPlan(
                entry="—",
                stop_loss="—",
                take_profit="—",
                risk_reward="—",
                target_liquidity="None",
                trade_direction="NO TRADE",
                notes=["Insufficient price geometry — cannot form a valid risk plan."],
            )

        avg = ctx.avg_range or 1.0
        buffer = max(avg * 0.35, 0.25)
        last = ctx.last_close
        swing_high = ctx.swing_high if ctx.swing_high is not None else (ctx.range_high or last + avg * 2)
        swing_low = ctx.swing_low if ctx.swing_low is not None else (ctx.range_low or last - avg * 2)
        range_high = ctx.range_high if ctx.range_high is not None else swing_high
        range_low = ctx.range_low if ctx.range_low is not None else swing_low

        notes: list[str] = [
            "Entry/SL/TP use chart-relative geometry from screenshots (not broker ticks).",
        ]

        if direction == "BUY":
            entry = min(last, (swing_low + last) / 2.0)
            stop = swing_low - buffer
            target_liq = "Buy-side liquidity above swing highs"
            take = max(swing_high, range_high)
            if h4.equal_highs or h1.equal_highs:
                take = max(take, range_high)
                target_liq = "Equal highs / external buy-side liquidity"
            if take <= entry:
                take = entry + max(buffer * 3.0, avg * 2.5)
            risk = entry - stop
            reward = take - entry
        else:
            entry = max(last, (swing_high + last) / 2.0)
            stop = swing_high + buffer
            target_liq = "Sell-side liquidity below swing lows"
            take = min(swing_low, range_low)
            if h4.equal_lows or h1.equal_lows:
                take = min(take, range_low)
                target_liq = "Equal lows / external sell-side liquidity"
            if take >= entry:
                take = entry - max(buffer * 3.0, avg * 2.5)
            risk = stop - entry
            reward = entry - take

        if risk <= 0 or reward <= 0:
            return RiskPlan(
                trade_direction="NO TRADE",
                notes=["Invalid risk geometry — refusing forced trade."],
            )

        rr = reward / risk
        if rr < 1.5:
            notes.append(f"Risk/reward {rr:.2f} below 1.5 minimum — trade rejected.")
            return RiskPlan(
                entry=_fmt(entry),
                stop_loss=_fmt(stop),
                take_profit=_fmt(take),
                risk_reward=f"{rr:.2f}",
                target_liquidity=target_liq,
                trade_direction="NO TRADE",
                notes=notes,
            )

        notes.append(f"Target liquidity: {target_liq}.")
        return RiskPlan(
            entry=_fmt(entry),
            stop_loss=_fmt(stop),
            take_profit=_fmt(take),
            risk_reward=f"{rr:.2f}",
            target_liquidity=target_liq,
            trade_direction=direction,
            notes=notes,
        )
