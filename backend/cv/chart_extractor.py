"""Chart Extractor — ROI, pair, timeframe, price scale, boundaries."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cv.models import ChartMeta
from vision.chart_parser import parse_chart_labels
from vision.chart_roi import detect_chart_roi


@dataclass
class ChartExtraction:
    meta: ChartMeta
    chart_bgr: np.ndarray
    chart_gray: np.ndarray
    roi_confidence: float


class ChartExtractor:
    def extract(
        self,
        original_bgr: np.ndarray,
        enhanced_bgr: np.ndarray,
        gray: np.ndarray,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartExtraction:
        labels = parse_chart_labels(original_bgr, expected_timeframe=expected_timeframe)
        roi = detect_chart_roi(enhanced_bgr, gray)

        # Chart-relative scale calibrated to the extracted ROI height.
        # Absolute broker prices remain Unknown without axis OCR — never invent them.
        h = max(int(roi.height), 1)
        price_scale = {
            "axis_min": 0.0,
            "axis_max": 100.0,
            "unit": "chart_relative",
            "roi_height_px": h,
            "roi_width_px": int(roi.width),
            "normalized": True,
            "absolute_prices": False,
            "note": "Relative 0–100 scale on ROI; absolute prices Unknown without axis ticks.",
        }

        meta = ChartMeta(
            pair=labels.pair if labels.pair else "Unknown",
            timeframe=labels.timeframe if labels.timeframe else "Unknown",
            detected_timeframe_label=labels.detected_timeframe_label,
            price_scale=price_scale,
            chart_bounds={
                "x": roi.x,
                "y": roi.y,
                "width": roi.width,
                "height": roi.height,
            },
            session_labels=list(labels.session_labels),
            pair_confidence=labels.pair_confidence,
            timeframe_confidence=labels.timeframe_confidence,
            roi_confidence=float(roi.confidence),
        )
        return ChartExtraction(
            meta=meta,
            chart_bgr=roi.image,
            chart_gray=roi.gray,
            roi_confidence=roi.confidence,
        )
