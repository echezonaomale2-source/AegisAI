"""Premium / discount and supply / demand zone classification."""

from __future__ import annotations

from dataclasses import dataclass, field

from ml.swing_detector import SwingPoint, split_swings
from vision.candle_detector import Candle


@dataclass
class ZoneResult:
    supply_zone: bool
    demand_zone: bool
    premium: str
    discount: str
    confidence: float = 0.0
    notes: list[str] = field(default_factory=list)


def analyze_zones(candles: list[Candle], swings: list[SwingPoint]) -> ZoneResult:
    if len(candles) < 3:
        return ZoneResult(
            supply_zone=False,
            demand_zone=False,
            premium="Unknown",
            discount="Unknown",
            confidence=0.0,
        )

    highs, lows = split_swings(swings)
    if highs and lows:
        range_high = max(h.price for h in highs)
        range_low = min(l.price for l in lows)
    else:
        range_high = max(c.high for c in candles)
        range_low = min(c.low for c in candles)

    span = max(range_high - range_low, 1e-6)
    equilibrium = range_low + span * 0.5
    last = candles[-1].close

    # Premium = upper 50%, Discount = lower 50%.
    in_premium = last >= equilibrium
    in_discount = last < equilibrium

    # Supply near highs with bearish reaction; demand near lows with bullish reaction.
    supply = False
    demand = False
    notes: list[str] = []
    near_high = last >= range_high - span * 0.2
    near_low = last <= range_low + span * 0.2
    if near_high and (not candles[-1].bullish or candles[-1].close < candles[-1].open):
        supply = True
        notes.append("Price reacting in supply / premium territory.")
    if near_low and (candles[-1].bullish or candles[-1].close > candles[-1].open):
        demand = True
        notes.append("Price reacting in demand / discount territory.")

    # Also mark latent zones from OB-like extremes.
    if not supply and near_high:
        supply = True
    if not demand and near_low:
        demand = True

    return ZoneResult(
        supply_zone=supply,
        demand_zone=demand,
        premium="Yes" if in_premium else "No",
        discount="Yes" if in_discount else "No",
        confidence=82.0 if highs and lows else 60.0,
        notes=notes,
    )
