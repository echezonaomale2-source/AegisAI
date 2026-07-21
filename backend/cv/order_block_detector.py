"""Order Block Detector — bullish/bearish OBs with high/low geometry + confidence."""

from __future__ import annotations

from cv.models import FeatureObject
from ml.order_block_fvg import analyze_order_blocks_and_fvg
from vision.candle_detector import Candle


class OrderBlockDetector:
    def detect(self, legacy_candles: list[Candle]) -> list[FeatureObject]:
        if len(legacy_candles) < 5:
            return [
                FeatureObject(
                    id="ob_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                )
            ]

        result = analyze_order_blocks_and_fvg(legacy_candles)
        features: list[FeatureObject] = []
        conf = result.confidence.get("order_block", 0.0)

        if result.bullish_order_block:
            loc: dict = {}
            if result.bullish_ob_zone:
                loc = {
                    "high": result.bullish_ob_zone.high,
                    "low": result.bullish_ob_zone.low,
                    "index": result.bullish_ob_zone.candle_index,
                }
            features.append(
                FeatureObject(
                    id="ob_bullish_primary",
                    type="bullish_order_block",
                    location=loc,
                    confidence=conf,
                    supporting_candles=(
                        [result.bullish_ob_zone.candle_index]
                        if result.bullish_ob_zone
                        else [c.index for c in legacy_candles[-12:]]
                    ),
                    label="Bullish Order Block",
                    notes=[n for n in result.notes if "Bullish" in n][:2],
                )
            )
        if result.bearish_order_block:
            loc = {}
            if result.bearish_ob_zone:
                loc = {
                    "high": result.bearish_ob_zone.high,
                    "low": result.bearish_ob_zone.low,
                    "index": result.bearish_ob_zone.candle_index,
                }
            features.append(
                FeatureObject(
                    id="ob_bearish_primary",
                    type="bearish_order_block",
                    location=loc,
                    confidence=conf,
                    supporting_candles=(
                        [result.bearish_ob_zone.candle_index]
                        if result.bearish_ob_zone
                        else [c.index for c in legacy_candles[-12:]]
                    ),
                    label="Bearish Order Block",
                    notes=[n for n in result.notes if "Bearish" in n][:2],
                )
            )

        if len(legacy_candles) >= 3:
            last = legacy_candles[-1]
            prev = legacy_candles[-3]
            mitigated = (
                (prev.bullish and last.low <= max(prev.open, prev.close))
                or ((not prev.bullish) and last.high >= min(prev.open, prev.close))
            )
            if mitigated and (result.bullish_order_block or result.bearish_order_block):
                features.append(
                    FeatureObject(
                        id="ob_mitigation_primary",
                        type="mitigation",
                        location={"mitigated": True, "index": prev.index},
                        confidence=68.0,
                        supporting_candles=[prev.index, last.index],
                        label="Order Block Mitigation",
                        relationships=[f.id for f in features if "ob_" in f.id],
                    )
                )

        if not features:
            features.append(
                FeatureObject(
                    id="ob_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Order blocks not detected confidently."],
                )
            )
        return features
