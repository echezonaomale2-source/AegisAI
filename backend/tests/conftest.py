"""Helpers to synthesize chart-like images for unit tests."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from vision.candle_detector import Candle


def make_synthetic_candles(pattern: str = "bullish") -> list[Candle]:
    candles: list[Candle] = []
    price = 40.0
    for i in range(40):
        if pattern == "bullish":
            open_p = price
            close_p = price + 1.2 + (i % 3) * 0.2
            high_p = close_p + 0.6
            low_p = open_p - 0.4
            price = close_p
            bullish = True
        elif pattern == "bearish":
            open_p = price
            close_p = price - 1.2 - (i % 3) * 0.2
            high_p = open_p + 0.4
            low_p = close_p - 0.6
            price = close_p
            bullish = False
        else:
            open_p = 50 + ((-1) ** i) * 0.8
            close_p = 50 + ((-1) ** (i + 1)) * 0.8
            high_p = max(open_p, close_p) + 0.5
            low_p = min(open_p, close_p) - 0.5
            bullish = close_p >= open_p

        candles.append(
            Candle(
                index=i,
                x_center=float(i * 10),
                open=open_p,
                high=high_p,
                low=low_p,
                close=close_p,
                bullish=bullish,
            )
        )
    return candles


def render_synthetic_chart(
    path: Path,
    candles: list[Candle] | None = None,
    pair_text: str = "EURUSD",
    timeframe_text: str = "4H",
) -> Path:
    candles = candles or make_synthetic_candles("bullish")
    width, height = 960, 640
    image = np.zeros((height, width, 3), dtype=np.uint8)
    image[:] = (18, 16, 12)  # dark BGR

    # Fake chrome / toolbar regions.
    image[0:36, :] = (40, 40, 40)
    image[:, 0:28] = (35, 35, 35)
    image[height - 30 :, :] = (45, 45, 45)

    cv2.putText(
        image,
        f"{pair_text}  {timeframe_text}",
        (40, 26),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7,
        (220, 220, 220),
        2,
        cv2.LINE_AA,
    )

    chart_top, chart_bottom = 50, height - 40
    chart_left, chart_right = 40, width - 30
    chart_h = chart_bottom - chart_top
    chart_w = chart_right - chart_left

    prices = [c.high for c in candles] + [c.low for c in candles]
    p_min, p_max = min(prices), max(prices)
    span = max(p_max - p_min, 1e-6)

    def y_of(price: float) -> int:
        norm = (price - p_min) / span
        return int(chart_bottom - norm * chart_h)

    step = max(chart_w // max(len(candles), 1), 6)
    for i, candle in enumerate(candles):
        x = chart_left + i * step + step // 2
        if x >= chart_right - 2:
            break
        color = (80, 200, 80) if candle.bullish else (60, 60, 220)
        y_high = y_of(candle.high)
        y_low = y_of(candle.low)
        y_open = y_of(candle.open)
        y_close = y_of(candle.close)
        cv2.line(image, (x, y_high), (x, y_low), (180, 180, 180), 1)
        top = min(y_open, y_close)
        bottom = max(y_open, y_close)
        cv2.rectangle(image, (x - 2, top), (x + 2, max(bottom, top + 1)), color, -1)

    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), image)
    return path
