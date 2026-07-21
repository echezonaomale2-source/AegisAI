"""Liquidity Detector — sweeps, equal highs/lows, internal/external pools."""

from __future__ import annotations

from cv.models import FeatureObject
from ml.liquidity_analyzer import analyze_liquidity
from ml.swing_detector import detect_swings
from vision.candle_detector import Candle


class LiquidityDetector:
    def detect(self, legacy_candles: list[Candle]) -> list[FeatureObject]:
        if len(legacy_candles) < 5:
            return [
                FeatureObject(
                    id="liquidity_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Insufficient candles for liquidity detection."],
                )
            ]

        swings = detect_swings(legacy_candles)
        result = analyze_liquidity(legacy_candles, swings)
        features: list[FeatureObject] = []

        if result.liquidity_sweep:
            features.append(
                FeatureObject(
                    id="liquidity_sweep_primary",
                    type="liquidity_sweep",
                    location={"label": result.liquidity},
                    confidence=result.confidence.get("liquidity_sweep", 70.0),
                    supporting_candles=[legacy_candles[-1].index],
                    label="Liquidity Sweep",
                    notes=result.notes[:2],
                )
            )
        if result.equal_highs:
            features.append(
                FeatureObject(
                    id="equal_highs_primary",
                    type="equal_highs",
                    confidence=result.confidence.get("liquidity", 70.0),
                    supporting_candles=[c.index for c in legacy_candles[-10:]],
                    label="Equal Highs",
                )
            )
        if result.equal_lows:
            features.append(
                FeatureObject(
                    id="equal_lows_primary",
                    type="equal_lows",
                    confidence=result.confidence.get("liquidity", 70.0),
                    supporting_candles=[c.index for c in legacy_candles[-10:]],
                    label="Equal Lows",
                )
            )

        # Emit internal / external liquidity when analyzer flags them
        if getattr(result, "internal_liquidity", False):
            features.append(
                FeatureObject(
                    id="liquidity_internal",
                    type="liquidity",
                    location={"kind": "internal"},
                    confidence=result.confidence.get("liquidity", 60.0),
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="Internal Liquidity",
                )
            )
        if getattr(result, "external_liquidity", False):
            hi = max(c.high for c in legacy_candles)
            lo = min(c.low for c in legacy_candles)
            features.append(
                FeatureObject(
                    id="liquidity_external",
                    type="liquidity",
                    location={"kind": "external", "high": hi, "low": lo},
                    confidence=result.confidence.get("liquidity", 60.0),
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="External Liquidity",
                )
            )

        if result.liquidity not in {"None Detected", "Unknown", ""}:
            features.append(
                FeatureObject(
                    id="liquidity_pool_primary",
                    type="liquidity",
                    location={"label": result.liquidity},
                    confidence=result.confidence.get("liquidity", 60.0),
                    supporting_candles=[c.index for c in legacy_candles[-8:]],
                    label=result.liquidity,
                    relationships=[
                        f.id
                        for f in features
                        if f.type in {"liquidity_sweep", "equal_highs", "equal_lows"}
                    ],
                )
            )
        elif not features:
            features.append(
                FeatureObject(
                    id="liquidity_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Liquidity could not be detected confidently."],
                )
            )

        return features
