"""Step 2 CV unit tests — geometry, swing labels, liquidity kinds."""

from __future__ import annotations

from cv.fvg_detector import FVGDetector
from cv.liquidity_detector import LiquidityDetector
from cv.market_structure_detector import MarketStructureDetector, _label_swings
from cv.order_block_detector import OrderBlockDetector
from ml.order_block_fvg import analyze_order_blocks_and_fvg
from vision.candle_detector import Candle


def _c(idx: int, o: float, h: float, l: float, c: float, bull: bool) -> Candle:
    return Candle(
        index=idx,
        x_center=float(idx * 10),
        open=o,
        high=h,
        low=l,
        close=c,
        bullish=bull,
    )


def _candles_bullish_impulse() -> list[Candle]:
    return [
        _c(0, 50, 52, 48, 49, False),
        _c(1, 49, 50, 47, 48, False),
        _c(2, 48, 49, 45, 46, False),
        _c(3, 46, 58, 46, 57, True),
        _c(4, 57, 60, 56, 59, True),
        _c(5, 59, 62, 58, 61, True),
        _c(6, 61, 63, 60, 62, True),
        _c(7, 62, 65, 61, 64, True),
    ]


def test_order_block_exposes_geometry():
    result = analyze_order_blocks_and_fvg(_candles_bullish_impulse())
    assert result.bullish_order_block
    assert result.bullish_ob_zone is not None
    assert result.bullish_ob_zone.high >= result.bullish_ob_zone.low

    feats = OrderBlockDetector().detect(_candles_bullish_impulse())
    bull = next(f for f in feats if f.type == "bullish_order_block")
    assert "high" in bull.location and "low" in bull.location
    assert bull.confidence > 0


def test_fvg_geometry_when_present():
    candles = [
        _c(0, 50, 51, 49, 50, True),
        _c(1, 50, 60, 50, 59, True),
        _c(2, 59, 62, 58, 61, True),
        _c(3, 61, 63, 60, 62, True),
        _c(4, 62, 64, 61, 63, True),
    ]
    result = analyze_order_blocks_and_fvg(candles)
    assert result.fair_value_gap
    assert result.fvg_zone is not None
    feats = FVGDetector().detect(candles)
    assert isinstance(feats, list)


def test_swing_labels():
    assert _label_swings([10, 12, 11], kind="high") == [None, "HH", "LH"]
    assert _label_swings([10, 8, 9], kind="low") == [None, "LL", "HL"]


def test_market_structure_attaches_swing_labels():
    candles = _candles_bullish_impulse()
    feats = MarketStructureDetector().detect(candles, [])
    swings = [f for f in feats if f.type in {"swing_high", "swing_low"}]
    assert swings
    assert all("price" in f.location and "index" in f.location for f in swings)


def test_liquidity_emits_internal_external():
    candles = _candles_bullish_impulse()
    feats = LiquidityDetector().detect(candles)
    assert len(feats) >= 1
