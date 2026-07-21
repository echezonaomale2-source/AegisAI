"""Image preprocessing for chart screenshots."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class PreprocessResult:
    original: np.ndarray
    enhanced: np.ndarray
    gray: np.ndarray
    sharpness: float
    width: int
    height: int
    quality_ok: bool
    quality_message: str | None = None


def load_image(path: str) -> np.ndarray:
    image = cv2.imread(path, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Unable to read image file.")
    return image


def measure_sharpness(gray: np.ndarray) -> float:
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())


def enhance_chart_image(bgr: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Denoise, boost local contrast, and lightly sharpen."""
    denoised = cv2.fastNlMeansDenoisingColored(bgr, None, 5, 5, 7, 21)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
    l_enhanced = clahe.apply(l_channel)
    lab_enhanced = cv2.merge((l_enhanced, a_channel, b_channel))
    contrast = cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    blur = cv2.GaussianBlur(contrast, (0, 0), 1.1)
    sharpened = cv2.addWeighted(contrast, 1.35, blur, -0.35, 0)
    gray = cv2.cvtColor(sharpened, cv2.COLOR_BGR2GRAY)
    sharpness = measure_sharpness(gray)
    return sharpened, gray, sharpness


def preprocess_image(path: str, min_sharpness: float = 35.0) -> PreprocessResult:
    original = load_image(path)
    height, width = original.shape[:2]

    if width < 240 or height < 180:
        gray = cv2.cvtColor(original, cv2.COLOR_BGR2GRAY)
        return PreprocessResult(
            original=original,
            enhanced=original.copy(),
            gray=gray,
            sharpness=measure_sharpness(gray),
            width=width,
            height=height,
            quality_ok=False,
            quality_message="Image Quality Too Low",
        )

    enhanced, gray, sharpness = enhance_chart_image(original)
    quality_ok = sharpness >= min_sharpness
    return PreprocessResult(
        original=original,
        enhanced=enhanced,
        gray=gray,
        sharpness=sharpness,
        width=width,
        height=height,
        quality_ok=quality_ok,
        quality_message=None if quality_ok else "Image Quality Too Low",
    )
