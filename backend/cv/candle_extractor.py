"""Candle Extractor — OHLC sequence with body/wick geometry."""

from __future__ import annotations

import numpy as np

from cv.models import CandleOHLC
from vision.candle_detector import detect_candles


class CandleExtractor:
    def extract(self, chart_bgr: np.ndarray) -> list[CandleOHLC]:
        raw = detect_candles(chart_bgr)
        if not raw:
            return []

        n = max(len(raw) - 1, 1)
        candles: list[CandleOHLC] = []
        for i, c in enumerate(raw):
            body = abs(c.close - c.open)
            upper = max(0.0, c.high - max(c.open, c.close))
            lower = max(0.0, min(c.open, c.close) - c.low)
            # Confidence rises with clearer body vs noise.
            conf = 55.0 + min(35.0, body * 8.0) + min(10.0, (upper + lower) * 2.0)
            candles.append(
                CandleOHLC(
                    index=i,
                    open=c.open,
                    high=c.high,
                    low=c.low,
                    close=c.close,
                    bullish=c.bullish,
                    body_size=body,
                    upper_wick=upper,
                    lower_wick=lower,
                    relative_position=i / n,
                    confidence=min(100.0, conf),
                )
            )
        return candles

    def to_legacy_candles(self, candles: list[CandleOHLC]):
        """Bridge to existing ml analyzers that expect vision.Candle."""
        from vision.candle_detector import Candle

        return [
            Candle(
                index=c.index,
                x_center=c.relative_position * 1000.0,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                bullish=c.bullish,
            )
            for c in candles
        ]
