"""
Legacy ChartDetector facade — now delegates to the Phase 2 pipeline pieces.
Kept for backwards-compatible imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from vision.candle_detector import Candle, detect_candles
from vision.chart_roi import detect_chart_roi
from vision.preprocessing import preprocess_image


@dataclass
class ChartVisionFeatures:
    image_path: Path
    candles_detected: int = 0
    candles: list[Candle] = field(default_factory=list)
    structure_points: list[tuple[float, float]] | None = None
    liquidity_zones: list[dict] | None = None
    order_blocks: list[dict] | None = None
    fair_value_gaps: list[dict] | None = None
    quality_ok: bool = True
    quality_message: str | None = None
    roi_confidence: float = 0.0


class ChartDetector:
    def analyze(self, image_path: Path) -> ChartVisionFeatures:
        try:
            pre = preprocess_image(str(image_path))
        except ValueError as exc:
            return ChartVisionFeatures(
                image_path=image_path,
                quality_ok=False,
                quality_message=str(exc),
            )

        if not pre.quality_ok:
            return ChartVisionFeatures(
                image_path=image_path,
                quality_ok=False,
                quality_message=pre.quality_message,
            )

        roi = detect_chart_roi(pre.enhanced, pre.gray)
        candles = detect_candles(roi.image)
        return ChartVisionFeatures(
            image_path=image_path,
            candles_detected=len(candles),
            candles=candles,
            quality_ok=True,
            roi_confidence=roi.confidence,
        )
