"""Liquidity, equal highs/lows, sweeps, internal/external liquidity."""

from __future__ import annotations

from dataclasses import dataclass, field

from ml.swing_detector import SwingPoint, split_swings
from vision.candle_detector import Candle


@dataclass
class LiquidityResult:
    liquidity: str
    liquidity_sweep: bool
    equal_highs: bool
    equal_lows: bool
    internal_liquidity: bool
    external_liquidity: bool
    confidence: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _near_equal(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def analyze_liquidity(candles: list[Candle], swings: list[SwingPoint]) -> LiquidityResult:
    highs, lows = split_swings(swings)
    if not candles:
        return LiquidityResult(
            liquidity="None Detected",
            liquidity_sweep=False,
            equal_highs=False,
            equal_lows=False,
            internal_liquidity=False,
            external_liquidity=False,
            confidence={"liquidity": 0, "liquidity_sweep": 0},
        )

    price_span = max(c.high for c in candles) - min(c.low for c in candles)
    tol = max(price_span * 0.004, 0.15)

    equal_highs = False
    equal_lows = False
    if len(highs) >= 2:
        equal_highs = any(
            _near_equal(highs[i].price, highs[j].price, tol)
            for i in range(len(highs))
            for j in range(i + 1, len(highs))
        )
    if len(lows) >= 2:
        equal_lows = any(
            _near_equal(lows[i].price, lows[j].price, tol)
            for i in range(len(lows))
            for j in range(i + 1, len(lows))
        )

    last = candles[-1]
    sweep = False
    liquidity_label = "None Detected"
    notes: list[str] = []

    if highs:
        ref_high = max(h.price for h in highs[-3:])
        # Sweep: wick beyond liquidity then close back inside.
        if last.high > ref_high + tol and last.close < ref_high:
            sweep = True
            liquidity_label = "Liquidity Sweep"
            notes.append("Buy-side liquidity swept above recent highs.")
        elif last.close > ref_high:
            liquidity_label = "Above Highs"
            notes.append("Price trading above recent swing highs.")

    if lows:
        ref_low = min(l.price for l in lows[-3:])
        if last.low < ref_low - tol and last.close > ref_low:
            sweep = True
            liquidity_label = "Liquidity Sweep"
            notes.append("Sell-side liquidity swept below recent lows.")
        elif last.close < ref_low and liquidity_label == "None Detected":
            liquidity_label = "Below Lows"
            notes.append("Price trading below recent swing lows.")

    if equal_highs and liquidity_label == "None Detected":
        liquidity_label = "Equal Highs"
    if equal_lows and liquidity_label == "None Detected":
        liquidity_label = "Equal Lows"

    # Internal = recent minor swings; external = extremes of visible range.
    internal = len(swings) >= 4
    external = bool(highs and lows)

    liq_conf = 84.0 if liquidity_label != "None Detected" else 35.0
    sweep_conf = 83.0 if sweep else 25.0
    if equal_highs or equal_lows:
        liq_conf = max(liq_conf, 80.0)

    return LiquidityResult(
        liquidity=liquidity_label,
        liquidity_sweep=sweep,
        equal_highs=equal_highs,
        equal_lows=equal_lows,
        internal_liquidity=internal,
        external_liquidity=external,
        confidence={
            "liquidity": liq_conf,
            "liquidity_sweep": sweep_conf,
        },
        notes=notes,
    )
