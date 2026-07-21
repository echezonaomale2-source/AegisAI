"""Swing high / swing low detection from candle series."""

from __future__ import annotations

from dataclasses import dataclass

from vision.candle_detector import Candle


@dataclass
class SwingPoint:
    index: int
    price: float
    kind: str  # "high" | "low"


def detect_swings(candles: list[Candle], left: int = 2, right: int = 2) -> list[SwingPoint]:
    if len(candles) < 3:
        return []

    fractal: list[SwingPoint] = []
    if len(candles) >= left + right + 1:
        for i in range(left, len(candles) - right):
            window = candles[i - left : i + right + 1]
            high = candles[i].high
            low = candles[i].low
            if all(high >= c.high for c in window):
                fractal.append(SwingPoint(index=i, price=high, kind="high"))
            if all(low <= c.low for c in window):
                fractal.append(SwingPoint(index=i, price=low, kind="low"))

    cleaned = _dedupe_same_kind(fractal)
    highs = [s for s in cleaned if s.kind == "high"]
    lows = [s for s in cleaned if s.kind == "low"]
    if len(highs) >= 2 and len(lows) >= 2:
        return cleaned

    zigzag = _zigzag_swings(candles)
    return zigzag if len(zigzag) >= len(cleaned) else cleaned


def _dedupe_same_kind(swings: list[SwingPoint]) -> list[SwingPoint]:
    cleaned: list[SwingPoint] = []
    for swing in swings:
        if cleaned and cleaned[-1].kind == swing.kind:
            if swing.kind == "high" and swing.price >= cleaned[-1].price:
                cleaned[-1] = swing
            elif swing.kind == "low" and swing.price <= cleaned[-1].price:
                cleaned[-1] = swing
            continue
        cleaned.append(swing)
    return cleaned


def _zigzag_swings(candles: list[Candle]) -> list[SwingPoint]:
    span = max(c.high for c in candles) - min(c.low for c in candles)
    threshold = max(span * 0.025, 0.3)

    swings: list[SwingPoint] = []
    # Start by tracking whichever extreme moves first.
    mode = "undecided"
    extreme_idx = 0
    extreme_high = candles[0].high
    extreme_low = candles[0].low

    for i, candle in enumerate(candles):
        if mode == "undecided":
            if candle.high >= extreme_high:
                extreme_high = candle.high
                extreme_idx = i
            if candle.low <= extreme_low:
                extreme_low = candle.low
                # Prefer low extreme index update only if clearer.
                if extreme_high - candle.low >= threshold:
                    swings.append(
                        SwingPoint(index=extreme_idx, price=extreme_high, kind="high")
                    )
                    mode = "down"
                    extreme_idx = i
                    extreme_low = candle.low
                elif candle.high - extreme_low >= threshold:
                    swings.append(
                        SwingPoint(index=i if candle.low == extreme_low else 0, price=extreme_low, kind="low")
                    )
                    mode = "up"
                    extreme_idx = i
                    extreme_high = candle.high
            continue

        if mode == "up":
            if candle.high >= extreme_high:
                extreme_high = candle.high
                extreme_idx = i
            elif extreme_high - candle.low >= threshold:
                swings.append(SwingPoint(index=extreme_idx, price=extreme_high, kind="high"))
                mode = "down"
                extreme_idx = i
                extreme_low = candle.low
        else:  # mode == "down"
            if candle.low <= extreme_low:
                extreme_low = candle.low
                extreme_idx = i
            elif candle.high - extreme_low >= threshold:
                swings.append(SwingPoint(index=extreme_idx, price=extreme_low, kind="low"))
                mode = "up"
                extreme_idx = i
                extreme_high = candle.high

    if mode == "up":
        swings.append(SwingPoint(index=extreme_idx, price=extreme_high, kind="high"))
    elif mode == "down":
        swings.append(SwingPoint(index=extreme_idx, price=extreme_low, kind="low"))

    return _dedupe_same_kind(swings)


def split_swings(swings: list[SwingPoint]) -> tuple[list[SwingPoint], list[SwingPoint]]:
    highs = [s for s in swings if s.kind == "high"]
    lows = [s for s in swings if s.kind == "low"]
    return highs, lows
