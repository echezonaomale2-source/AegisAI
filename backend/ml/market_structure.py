"""Backwards-compatible market structure module — delegates to Phase 2 analyzers."""

from __future__ import annotations

from dataclasses import dataclass

from ml.structure_analyzer import analyze_market_structure
from ml.swing_detector import detect_swings
from vision.chart_detector import ChartVisionFeatures


@dataclass
class StructureSignal:
    bias: str
    confidence: float
    notes: list[str]


class MarketStructureAnalyzer:
    def analyze(
        self,
        features_4h: ChartVisionFeatures,
        features_1h: ChartVisionFeatures,
        features_15m: ChartVisionFeatures,
    ) -> StructureSignal:
        notes: list[str] = []
        confidences: list[float] = []

        for label, features in (
            ("4H", features_4h),
            ("1H", features_1h),
            ("15M", features_15m),
        ):
            if not features.quality_ok or not features.candles:
                notes.append(f"{label}: insufficient chart data.")
                continue
            swings = detect_swings(features.candles)
            result = analyze_market_structure(features.candles, swings)
            confidences.append(result.confidence.get("trend", 0.0))
            notes.append(f"{label}: {result.trend} / {result.market_structure}")

        return StructureSignal(
            bias="NO TRADE",
            confidence=sum(confidences) / len(confidences) if confidences else 0.0,
            notes=notes or ["No structure extracted."],
        )
