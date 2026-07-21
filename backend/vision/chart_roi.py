"""Detect and crop the candlestick chart area, ignoring UI chrome."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class ChartROI:
    image: np.ndarray
    gray: np.ndarray
    x: int
    y: int
    width: int
    height: int
    confidence: float


def _largest_dark_region(bgr: np.ndarray) -> tuple[int, int, int, int] | None:
    """Find the largest dark rectangular region typical of chart canvases."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    # Dark backgrounds (TradingView / MT4 / cTrader night themes).
    dark = cv2.inRange(hsv, (0, 0, 0), (180, 90, 70))
    # Also keep muted navy panels.
    navy = cv2.inRange(hsv, (90, 20, 20), (140, 120, 95))
    mask = cv2.bitwise_or(dark, navy)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 15))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    height, width = bgr.shape[:2]
    image_area = float(width * height)
    best = None
    best_score = 0.0

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        area = w * h
        if area < image_area * 0.25:
            continue
        aspect = w / max(h, 1)
        if aspect < 0.8 or aspect > 4.5:
            continue
        # Prefer regions away from extreme edges (status / side rails).
        margin_penalty = 0.0
        if y < height * 0.02:
            margin_penalty += 0.05
        if x < width * 0.02:
            margin_penalty += 0.03
        score = (area / image_area) - margin_penalty
        if score > best_score:
            best_score = score
            best = (x, y, w, h)

    return best


def _heuristic_crop(bgr: np.ndarray) -> tuple[int, int, int, int]:
    """Fallback crop that strips status bars, sidebars, and bottom toolbars."""
    height, width = bgr.shape[:2]
    top = int(height * 0.08)
    bottom = int(height * 0.92)
    left = int(width * 0.04)
    right = int(width * 0.96)

    # Trim denser top chrome if a bright toolbar strip exists.
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    row_mean = gray.mean(axis=1)
    for y in range(top, min(top + int(height * 0.12), height - 1)):
        if row_mean[y] < row_mean.mean() * 0.85:
            top = y
            break

    return left, top, max(right - left, 1), max(bottom - top, 1)


def detect_chart_roi(bgr: np.ndarray, gray: np.ndarray | None = None) -> ChartROI:
    height, width = bgr.shape[:2]
    detected = _largest_dark_region(bgr)
    if detected is None:
        x, y, w, h = _heuristic_crop(bgr)
        confidence = 55.0
    else:
        x, y, w, h = detected
        # Inset slightly to drop axis labels and leftover chrome.
        pad_x = int(w * 0.02)
        pad_y = int(h * 0.03)
        x = min(max(x + pad_x, 0), width - 2)
        y = min(max(y + pad_y, 0), height - 2)
        w = max(min(w - 2 * pad_x, width - x), 1)
        h = max(min(h - 2 * pad_y, height - y), 1)
        confidence = 82.0

    crop = bgr[y : y + h, x : x + w].copy()
    if gray is None:
        crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    else:
        crop_gray = gray[y : y + h, x : x + w].copy()

    return ChartROI(
        image=crop,
        gray=crop_gray,
        x=x,
        y=y,
        width=w,
        height=h,
        confidence=confidence,
    )
