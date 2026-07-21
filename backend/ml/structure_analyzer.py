"""Market structure, BOS, CHOCH, trend, impulse/correction analysis."""

from __future__ import annotations

from dataclasses import dataclass, field

from ml.swing_detector import SwingPoint, split_swings
from vision.candle_detector import Candle


@dataclass
class StructureResult:
    trend: str
    market_structure: str
    bos: bool
    choch: bool
    impulse_move: bool
    correction_move: bool
    strong_rejection: bool
    weak_rejection: bool
    confidence: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _classify_structure(highs: list[SwingPoint], lows: list[SwingPoint]) -> tuple[str, str, float]:
    if len(highs) < 2 or len(lows) < 2:
        return "Unknown", "Unknown", 20.0

    hh = highs[-1].price > highs[-2].price
    lh = highs[-1].price < highs[-2].price
    hl = lows[-1].price > lows[-2].price
    ll = lows[-1].price < lows[-2].price

    if hh and hl:
        return "Bullish", "Higher Highs", 90.0
    if ll and lh:
        return "Bearish", "Lower Lows", 90.0
    if hh and ll:
        return "Range", "Expanding Range", 70.0
    if lh and hl:
        return "Range", "Contracting Range", 72.0
    if hh:
        return "Bullish", "Higher High", 75.0
    if hl:
        return "Bullish", "Higher Low", 75.0
    if ll:
        return "Bearish", "Lower Low", 75.0
    if lh:
        return "Bearish", "Lower High", 75.0
    return "Range", "Range", 60.0


def _detect_bos_choch(
    candles: list[Candle],
    highs: list[SwingPoint],
    lows: list[SwingPoint],
    trend: str,
) -> tuple[bool, bool, float, float, list[str]]:
    notes: list[str] = []
    bos = False
    choch = False
    bos_conf = 0.0
    choch_conf = 0.0

    if not candles or (not highs and not lows):
        return bos, choch, bos_conf, choch_conf, notes

    last_close = candles[-1].close
    last_high = candles[-1].high
    last_low = candles[-1].low

    if highs:
        prior_high = highs[-1].price
        # Break of structure to the upside.
        if last_close > prior_high or last_high > prior_high:
            if trend in {"Bullish", "Range", "Unknown"}:
                bos = True
                bos_conf = 92.0 if last_close > prior_high else 80.0
                notes.append("Upside BOS relative to last swing high.")
            if trend == "Bearish":
                choch = True
                choch_conf = 90.0 if last_close > prior_high else 78.0
                notes.append("Bullish CHOCH — bearish structure broken upward.")

    if lows:
        prior_low = lows[-1].price
        if last_close < prior_low or last_low < prior_low:
            if trend in {"Bearish", "Range", "Unknown"}:
                bos = True
                bos_conf = max(bos_conf, 92.0 if last_close < prior_low else 80.0)
                notes.append("Downside BOS relative to last swing low.")
            if trend == "Bullish":
                choch = True
                choch_conf = max(choch_conf, 90.0 if last_close < prior_low else 78.0)
                notes.append("Bearish CHOCH — bullish structure broken downward.")

    return bos, choch, bos_conf, choch_conf, notes


def _impulse_correction(candles: list[Candle]) -> tuple[bool, bool, float]:
    if len(candles) < 6:
        return False, False, 0.0
    recent = candles[-8:]
    net = recent[-1].close - recent[0].open
    ranges = [c.range for c in recent]
    avg_range = sum(ranges) / len(ranges)
    directional = abs(net) > avg_range * 2.2
    body_ratios = [abs(c.close - c.open) / c.range for c in recent]
    impulsive_bodies = sum(1 for r in body_ratios if r > 0.55) >= 3
    impulse = directional and impulsive_bodies
    correction = (not impulse) and abs(net) < avg_range * 1.2
    conf = 85.0 if impulse else (70.0 if correction else 40.0)
    return impulse, correction, conf


def _rejection(candles: list[Candle]) -> tuple[bool, bool, float]:
    if not candles:
        return False, False, 0.0
    c = candles[-1]
    upper = c.high - c.body_top
    lower = c.body_bottom - c.low
    body = abs(c.close - c.open)
    strong = False
    weak = False
    if lower > body * 1.8 and lower > upper:
        strong = True
    elif upper > body * 1.8 and upper > lower:
        strong = True
    elif lower > body * 1.1 or upper > body * 1.1:
        weak = True
    conf = 88.0 if strong else (65.0 if weak else 30.0)
    return strong, weak, conf


def analyze_market_structure(candles: list[Candle], swings: list[SwingPoint]) -> StructureResult:
    highs, lows = split_swings(swings)
    trend, market_structure, structure_conf = _classify_structure(highs, lows)
    bos, choch, bos_conf, choch_conf, notes = _detect_bos_choch(candles, highs, lows, trend)
    impulse, correction, move_conf = _impulse_correction(candles)
    strong_rej, weak_rej, rej_conf = _rejection(candles)

    trend_conf = structure_conf
    if trend == "Unknown":
        trend_conf = 15.0

    return StructureResult(
        trend=trend,
        market_structure=market_structure,
        bos=bos,
        choch=choch,
        impulse_move=impulse,
        correction_move=correction,
        strong_rejection=strong_rej,
        weak_rejection=weak_rej,
        confidence={
            "trend": trend_conf,
            "market_structure": structure_conf,
            "bos": bos_conf if bos else 20.0,
            "choch": choch_conf if choch else 20.0,
            "impulse": move_conf,
            "rejection": rej_conf,
        },
        notes=notes,
    )
