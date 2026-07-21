from ml.liquidity_analyzer import analyze_liquidity
from ml.order_block_fvg import analyze_order_blocks_and_fvg
from ml.structure_analyzer import analyze_market_structure
from ml.swing_detector import detect_swings
from ml.zone_analyzer import analyze_zones
from tests.conftest import make_synthetic_candles
from vision.candle_detector import Candle


def _wave_candles(bullish: bool = True) -> list[Candle]:
    """Build a clear HH/HL or LH/LL swing sequence."""
    candles: list[Candle] = []
    # Segments create explicit swings.
    if bullish:
        segments = [
            (30, 38),
            (36, 32),
            (33, 45),
            (43, 39),
            (40, 55),
            (53, 48),
            (49, 62),
        ]
    else:
        segments = [
            (70, 60),
            (62, 66),
            (65, 50),
            (52, 56),
            (55, 40),
            (42, 46),
            (45, 30),
        ]

    idx = 0
    for start, end in segments:
        steps = 5
        for s in range(steps):
            open_p = start + (end - start) * (s / steps)
            close_p = start + (end - start) * ((s + 1) / steps)
            high_p = max(open_p, close_p) + 0.4
            low_p = min(open_p, close_p) - 0.4
            candles.append(
                Candle(
                    index=idx,
                    x_center=float(idx * 8),
                    open=open_p,
                    high=high_p,
                    low=low_p,
                    close=close_p,
                    bullish=close_p >= open_p,
                )
            )
            idx += 1
    return candles


def test_bullish_structure_detection():
    candles = _wave_candles(bullish=True)
    swings = detect_swings(candles)
    result = analyze_market_structure(candles, swings)
    assert result.trend in {"Bullish", "Range"}
    assert result.confidence["trend"] > 0


def test_bearish_structure_detection():
    candles = _wave_candles(bullish=False)
    swings = detect_swings(candles)
    result = analyze_market_structure(candles, swings)
    assert result.trend in {"Bearish", "Range"}


def test_fvg_and_order_block_modules_run():
    candles = [
        Candle(0, 0, 10, 12, 9, 11, True),
        Candle(1, 10, 11, 13, 10, 12, True),
        Candle(2, 20, 20, 22, 19.5, 21, True),  # gap above candle 0 high
    ]
    # Explicit bullish FVG: c0.high=12 < c2.low=19.5
    candles[0] = Candle(0, 0, 10, 12, 9, 11, True)
    candles[1] = Candle(1, 10, 14, 16, 13, 15, True)
    candles[2] = Candle(2, 20, 20, 23, 19.5, 22, True)
    result = analyze_order_blocks_and_fvg(candles)
    assert result.fair_value_gap is True
    assert result.fvg_type == "Bullish FVG"


def test_liquidity_and_zones_modules_run():
    candles = make_synthetic_candles("bullish")
    swings = detect_swings(candles)
    liquidity = analyze_liquidity(candles, swings)
    zones = analyze_zones(candles, swings)
    assert liquidity.liquidity
    assert zones.premium in {"Yes", "No", "Unknown"}
    assert zones.discount in {"Yes", "No", "Unknown"}
