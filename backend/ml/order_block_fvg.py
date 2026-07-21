"""Order block and fair value gap detection with price geometry."""

from __future__ import annotations

from dataclasses import dataclass, field

from vision.candle_detector import Candle


@dataclass
class ZoneGeometry:
    high: float
    low: float
    candle_index: int
    mid_index: int | None = None


@dataclass
class OrderBlockFvgResult:
    bullish_order_block: bool
    bearish_order_block: bool
    fair_value_gap: bool
    fvg_type: str | None
    confidence: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)
    bullish_ob_zone: ZoneGeometry | None = None
    bearish_ob_zone: ZoneGeometry | None = None
    fvg_zone: ZoneGeometry | None = None


def _detect_order_blocks(
    candles: list[Candle],
) -> tuple[bool, bool, float, list[str], ZoneGeometry | None, ZoneGeometry | None]:
    notes: list[str] = []
    if len(candles) < 5:
        return False, False, 0.0, notes, None, None

    bullish_ob = False
    bearish_ob = False
    conf = 0.0
    bull_zone: ZoneGeometry | None = None
    bear_zone: ZoneGeometry | None = None

    for i in range(2, len(candles) - 1):
        prev = candles[i]
        nxt = candles[i + 1]
        move = abs(nxt.close - prev.open)
        if move < prev.range * 1.4:
            continue
        if (not prev.bullish) and nxt.close > prev.high:
            bullish_ob = True
            conf = max(conf, 88.0)
            bull_zone = ZoneGeometry(
                high=max(prev.open, prev.close, prev.high),
                low=min(prev.open, prev.close, prev.low),
                candle_index=prev.index,
            )
            notes.append(f"Bullish order block candidate near candle {prev.index}.")
        if prev.bullish and nxt.close < prev.low:
            bearish_ob = True
            conf = max(conf, 88.0)
            bear_zone = ZoneGeometry(
                high=max(prev.open, prev.close, prev.high),
                low=min(prev.open, prev.close, prev.low),
                candle_index=prev.index,
            )
            notes.append(f"Bearish order block candidate near candle {prev.index}.")

    if not bullish_ob and not bearish_ob:
        conf = 25.0
    return bullish_ob, bearish_ob, conf, notes, bull_zone, bear_zone


def _detect_fvg(
    candles: list[Candle],
) -> tuple[bool, str | None, float, list[str], ZoneGeometry | None]:
    notes: list[str] = []
    if len(candles) < 3:
        return False, None, 0.0, notes, None

    best_type: str | None = None
    best_gap = 0.0
    best_zone: ZoneGeometry | None = None
    for i in range(len(candles) - 2):
        left = candles[i]
        mid = candles[i + 1]
        right = candles[i + 2]
        if left.high < right.low:
            gap = right.low - left.high
            if gap > best_gap:
                best_gap = gap
                best_type = "Bullish FVG"
                best_zone = ZoneGeometry(
                    high=right.low,
                    low=left.high,
                    candle_index=left.index,
                    mid_index=mid.index,
                )
                notes.append(f"Bullish FVG between candles {left.index} and {right.index}.")
        if left.low > right.high:
            gap = left.low - right.high
            if gap > best_gap:
                best_gap = gap
                best_type = "Bearish FVG"
                best_zone = ZoneGeometry(
                    high=left.low,
                    low=right.high,
                    candle_index=left.index,
                    mid_index=mid.index,
                )
                notes.append(f"Bearish FVG between candles {left.index} and {right.index}.")

    if best_type is None:
        return False, None, 25.0, notes, None

    span = max(c.high for c in candles) - min(c.low for c in candles)
    conf = 90.0 if best_gap > span * 0.01 else 70.0
    return True, best_type, conf, notes, best_zone


def analyze_order_blocks_and_fvg(candles: list[Candle]) -> OrderBlockFvgResult:
    bull_ob, bear_ob, ob_conf, ob_notes, bull_zone, bear_zone = _detect_order_blocks(candles)
    has_fvg, fvg_type, fvg_conf, fvg_notes, fvg_zone = _detect_fvg(candles)
    return OrderBlockFvgResult(
        bullish_order_block=bull_ob,
        bearish_order_block=bear_ob,
        fair_value_gap=has_fvg,
        fvg_type=fvg_type,
        confidence={
            "order_block": ob_conf,
            "fair_value_gap": fvg_conf,
        },
        notes=ob_notes + fvg_notes,
        bullish_ob_zone=bull_zone,
        bearish_ob_zone=bear_zone,
        fvg_zone=fvg_zone,
    )
