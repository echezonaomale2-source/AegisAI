"""Candlestick extraction from chart ROI pixels."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class Candle:
    index: int
    x_center: float
    open: float
    high: float
    low: float
    close: float
    bullish: bool

    @property
    def body_top(self) -> float:
        return max(self.open, self.close)

    @property
    def body_bottom(self) -> float:
        return min(self.open, self.close)

    @property
    def range(self) -> float:
        return max(self.high - self.low, 1e-6)


def _color_masks(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)

    # Bullish (green / teal / cyan) bodies.
    bull_a = cv2.inRange(hsv, (35, 40, 40), (95, 255, 255))
    bull_b = cv2.inRange(hsv, (85, 30, 50), (110, 255, 255))
    bullish = cv2.bitwise_or(bull_a, bull_b)

    # Bearish (red / magenta / orange-red) bodies — hue wraps around 0.
    bear_a = cv2.inRange(hsv, (0, 50, 50), (15, 255, 255))
    bear_b = cv2.inRange(hsv, (160, 40, 50), (180, 255, 255))
    bearish = cv2.bitwise_or(bear_a, bear_b)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 3))
    bullish = cv2.morphologyEx(bullish, cv2.MORPH_CLOSE, kernel, iterations=1)
    bearish = cv2.morphologyEx(bearish, cv2.MORPH_CLOSE, kernel, iterations=1)
    return bullish, bearish


def _cluster_columns(mask: np.ndarray, min_width: int = 1) -> list[tuple[int, int]]:
    """Return inclusive [start, end] column ranges with candle-colored pixels."""
    if mask.size == 0:
        return []
    col_hits = (mask > 0).sum(axis=0)
    threshold = max(2, int(mask.shape[0] * 0.01))
    active = col_hits >= threshold
    ranges: list[tuple[int, int]] = []
    start = None
    for idx, flag in enumerate(active.tolist()):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            if idx - 1 - start + 1 >= min_width:
                ranges.append((start, idx - 1))
            start = None
    if start is not None and mask.shape[1] - 1 - start + 1 >= min_width:
        ranges.append((start, mask.shape[1] - 1))
    return ranges


def _y_to_price(y: float, height: int) -> float:
    """Map image y (top=0) to an upward price axis in [0, 100]."""
    if height <= 1:
        return 0.0
    return float(100.0 * (1.0 - (y / (height - 1))))


def _extract_from_band(
    band_mask: np.ndarray,
    wick_mask: np.ndarray,
    x0: int,
    x1: int,
    height: int,
    bullish: bool,
    index: int,
) -> Candle | None:
    slice_body = band_mask[:, x0 : x1 + 1]
    ys_body = np.where(slice_body > 0)[0]
    if len(ys_body) < 2:
        return None

    body_top_y = int(ys_body.min())
    body_bot_y = int(ys_body.max())

    slice_wick = wick_mask[:, max(x0 - 1, 0) : min(x1 + 2, wick_mask.shape[1])]
    ys_wick = np.where(slice_wick > 0)[0]
    if len(ys_wick) == 0:
        high_y, low_y = body_top_y, body_bot_y
    else:
        high_y = int(min(ys_wick.min(), body_top_y))
        low_y = int(max(ys_wick.max(), body_bot_y))

    open_p = _y_to_price(body_bot_y if bullish else body_top_y, height)
    close_p = _y_to_price(body_top_y if bullish else body_bot_y, height)
    high_p = _y_to_price(high_y, height)
    low_p = _y_to_price(low_y, height)

    if high_p < low_p:
        high_p, low_p = low_p, high_p

    return Candle(
        index=index,
        x_center=(x0 + x1) / 2.0,
        open=open_p,
        high=high_p,
        low=low_p,
        close=close_p,
        bullish=bullish,
    )


def detect_candles(bgr: np.ndarray) -> list[Candle]:
    """Detect ordered left→right candles from a chart ROI."""
    height, width = bgr.shape[:2]
    if height < 40 or width < 40:
        return []

    bullish_mask, bearish_mask = _color_masks(bgr)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    # Wick-like thin bright/dark strokes against dark theme.
    edges = cv2.Canny(gray, 40, 120)
    wick_mask = cv2.bitwise_or(edges, cv2.bitwise_or(bullish_mask, bearish_mask))

    bull_ranges = _cluster_columns(bullish_mask)
    bear_ranges = _cluster_columns(bearish_mask)

    candidates: list[tuple[float, Candle]] = []
    idx = 0
    for x0, x1 in bull_ranges:
        candle = _extract_from_band(bullish_mask, wick_mask, x0, x1, height, True, idx)
        if candle:
            candidates.append((candle.x_center, candle))
            idx += 1
    for x0, x1 in bear_ranges:
        candle = _extract_from_band(bearish_mask, wick_mask, x0, x1, height, False, idx)
        if candle:
            candidates.append((candle.x_center, candle))
            idx += 1

    if not candidates:
        return _fallback_intensity_candles(bgr)

    candidates.sort(key=lambda item: item[0])
    # Merge overlapping detections (same x band detected as both colors).
    merged: list[Candle] = []
    min_gap = max(2.0, width * 0.004)
    for _, candle in candidates:
        if merged and abs(candle.x_center - merged[-1].x_center) < min_gap:
            # Keep the taller / more expressive candle.
            if candle.range >= merged[-1].range:
                merged[-1] = candle
            continue
        merged.append(candle)

    for i, candle in enumerate(merged):
        candle.index = i
    return merged


def _fallback_intensity_candles(bgr: np.ndarray) -> list[Candle]:
    """
    Fallback when platform uses grayscale / nonstandard candle colors.
    Uses vertical activity strips as pseudo-candles.
    """
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    height, width = gray.shape
    blur = cv2.GaussianBlur(gray, (3, 3), 0)
    col_std = blur.std(axis=0)
    threshold = float(np.percentile(col_std, 70))
    active = col_std >= threshold
    ranges = []
    start = None
    for idx, flag in enumerate(active.tolist()):
        if flag and start is None:
            start = idx
        elif not flag and start is not None:
            if idx - start >= 2:
                ranges.append((start, idx - 1))
            start = None
    if start is not None and width - start >= 2:
        ranges.append((start, width - 1))

    candles: list[Candle] = []
    for i, (x0, x1) in enumerate(ranges[:180]):
        band = blur[:, x0 : x1 + 1]
        # Darker pixels on light bg OR brighter strokes on dark bg.
        profile = band.min(axis=1) if band.mean() > 90 else band.max(axis=1)
        # Find significant vertical span.
        if band.mean() > 90:
            ys = np.where(profile < band.mean() - 8)[0]
        else:
            ys = np.where(profile > band.mean() + 8)[0]
        if len(ys) < 3:
            continue
        high_y, low_y = int(ys.min()), int(ys.max())
        mid = (high_y + low_y) // 2
        open_p = _y_to_price(mid + (low_y - high_y) * 0.15, height)
        close_p = _y_to_price(mid - (low_y - high_y) * 0.15, height)
        bullish = close_p >= open_p
        candles.append(
            Candle(
                index=i,
                x_center=(x0 + x1) / 2.0,
                open=open_p,
                high=_y_to_price(high_y, height),
                low=_y_to_price(low_y, height),
                close=close_p,
                bullish=bullish,
            )
        )
    return candles
