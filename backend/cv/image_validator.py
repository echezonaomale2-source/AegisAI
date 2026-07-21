"""Image Validator — quality, crop, and candle visibility gates."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from vision.preprocessing import load_image, measure_sharpness, enhance_chart_image


@dataclass
class ValidationResult:
    ok: bool
    message: str | None
    sharpness: float
    quality_score: float
    original: np.ndarray | None = None
    enhanced: np.ndarray | None = None
    gray: np.ndarray | None = None


class ImageValidator:
    def __init__(
        self,
        min_sharpness: float = 35.0,
        min_width: int = 280,
        min_height: int = 200,
        min_edge_density: float = 0.008,
    ) -> None:
        self.min_sharpness = min_sharpness
        self.min_width = min_width
        self.min_height = min_height
        self.min_edge_density = min_edge_density

    def validate(self, path: str) -> ValidationResult:
        try:
            original = load_image(path)
        except ValueError:
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=0.0,
                quality_score=0.0,
            )

        height, width = original.shape[:2]
        if width < self.min_width or height < self.min_height:
            gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=measure_sharpness(gray),
                quality_score=10.0,
                original=original,
                gray=gray,
            )

        # Reject extreme crops (ultra-wide thin strips that hide structure).
        aspect = width / max(height, 1)
        if aspect > 5.5 or aspect < 0.55:
            gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=measure_sharpness(gray),
                quality_score=15.0,
                original=original,
                gray=gray,
            )

        enhanced, gray, sharpness = enhance_chart_image(original)
        if sharpness < self.min_sharpness:
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=sharpness,
                quality_score=max(5.0, min(40.0, sharpness)),
                original=original,
                enhanced=enhanced,
                gray=gray,
            )

        edges = cv2.Canny(gray, 40, 120)
        edge_density = float((edges > 0).mean())
        if edge_density < self.min_edge_density:
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=sharpness,
                quality_score=25.0,
                original=original,
                enhanced=enhanced,
                gray=gray,
            )

        # Heuristic: candles usually create vertical activity — reject empty walls.
        col_activity = (edges > 0).sum(axis=0)
        active_cols = float((col_activity > max(2, height * 0.01)).mean())
        if active_cols < 0.08:
            return ValidationResult(
                ok=False,
                message="Image Quality Too Low",
                sharpness=sharpness,
                quality_score=30.0,
                original=original,
                enhanced=enhanced,
                gray=gray,
            )

        quality = min(
            100.0,
            40.0
            + min(35.0, sharpness / 4.0)
            + min(15.0, edge_density * 800.0)
            + min(10.0, active_cols * 40.0),
        )
        return ValidationResult(
            ok=True,
            message=None,
            sharpness=sharpness,
            quality_score=round(quality, 1),
            original=original,
            enhanced=enhanced,
            gray=gray,
        )
