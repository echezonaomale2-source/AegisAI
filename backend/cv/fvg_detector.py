"""FVG Detector + supply/demand / premium/discount zone features with geometry."""

from __future__ import annotations

from cv.models import FeatureObject
from ml.order_block_fvg import analyze_order_blocks_and_fvg
from ml.swing_detector import detect_swings, split_swings
from ml.zone_analyzer import analyze_zones
from vision.candle_detector import Candle


class FVGDetector:
    def detect(self, legacy_candles: list[Candle]) -> list[FeatureObject]:
        features: list[FeatureObject] = []
        if len(legacy_candles) < 5:
            return [
                FeatureObject(
                    id="fvg_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                )
            ]

        ob_fvg = analyze_order_blocks_and_fvg(legacy_candles)
        swings = detect_swings(legacy_candles)
        highs, lows = split_swings(swings)
        zones = analyze_zones(legacy_candles, swings)
        conf = ob_fvg.confidence.get("fair_value_gap", 0.0)

        if ob_fvg.fair_value_gap and ob_fvg.fvg_type == "Bullish FVG":
            loc = {}
            if ob_fvg.fvg_zone:
                loc = {
                    "high": ob_fvg.fvg_zone.high,
                    "low": ob_fvg.fvg_zone.low,
                    "index": ob_fvg.fvg_zone.candle_index,
                }
            features.append(
                FeatureObject(
                    id="fvg_bullish_primary",
                    type="bullish_fvg",
                    location=loc,
                    confidence=conf,
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="Bullish FVG",
                    notes=ob_fvg.notes[-2:],
                )
            )
        elif ob_fvg.fair_value_gap and ob_fvg.fvg_type == "Bearish FVG":
            loc = {}
            if ob_fvg.fvg_zone:
                loc = {
                    "high": ob_fvg.fvg_zone.high,
                    "low": ob_fvg.fvg_zone.low,
                    "index": ob_fvg.fvg_zone.candle_index,
                }
            features.append(
                FeatureObject(
                    id="fvg_bearish_primary",
                    type="bearish_fvg",
                    location=loc,
                    confidence=conf,
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="Bearish FVG",
                    notes=ob_fvg.notes[-2:],
                )
            )
        else:
            features.append(
                FeatureObject(
                    id="fvg_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Fair value gap not detected confidently."],
                )
            )

        range_high = max((h.price for h in highs), default=max(c.high for c in legacy_candles))
        range_low = min((low.price for low in lows), default=min(c.low for c in legacy_candles))
        span = max(range_high - range_low, 1e-6)

        if zones.supply_zone:
            features.append(
                FeatureObject(
                    id="zone_supply",
                    type="supply_zone",
                    location={
                        "high": range_high,
                        "low": range_high - span * 0.15,
                        "index": legacy_candles[-1].index,
                    },
                    confidence=zones.confidence,
                    supporting_candles=[legacy_candles[-1].index],
                    label="Supply Zone",
                )
            )
        if zones.demand_zone:
            features.append(
                FeatureObject(
                    id="zone_demand",
                    type="demand_zone",
                    location={
                        "high": range_low + span * 0.15,
                        "low": range_low,
                        "index": legacy_candles[-1].index,
                    },
                    confidence=zones.confidence,
                    supporting_candles=[legacy_candles[-1].index],
                    label="Demand Zone",
                )
            )
        if zones.premium == "Yes":
            features.append(
                FeatureObject(
                    id="zone_premium",
                    type="premium",
                    confidence=zones.confidence,
                    supporting_candles=[legacy_candles[-1].index],
                    label="Premium",
                )
            )
        elif zones.discount == "Yes":
            features.append(
                FeatureObject(
                    id="zone_discount",
                    type="discount",
                    confidence=zones.confidence,
                    supporting_candles=[legacy_candles[-1].index],
                    label="Discount",
                )
            )

        return features
