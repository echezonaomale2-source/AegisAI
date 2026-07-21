"""Engine 3 — Feature Extraction Engine: MarketModel → FeatureCollection."""

from __future__ import annotations

from cognitive.events import EVT_FEATURES_EXTRACTED, EventBus
from cognitive.models.features import CognitiveFeature, FeatureCollection
from cognitive.models.market import MarketModel
from core.engines.feature_extractor import FeatureExtractor
from core.logging_setup import get_logger
from core.models.chart import ChartModel

log = get_logger("cognitive.features")


class FeatureExtractionEngine:
    """Convert MarketModel into structured features with confidence & relationships."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self._extractor = FeatureExtractor()
        self._bus = bus

    def extract(self, market: MarketModel) -> FeatureCollection:
        if not market.is_usable:
            return FeatureCollection(
                timeframe=market.timeframe,
                pair=market.pair,
                missing=["usable_market"],
                notes=[market.error or "Market not usable"],
            )

        chart = market.source_chart or ChartModel(
            status=market.status,
            pair=market.pair,
            timeframe=market.timeframe,
            candles=list(market.candles),
            swing_points=list(market.swing_points),
            trend=market.trend,
            market_structure_label=market.structure_label,
            bos=market.bos,
            choch=market.choch,
            liquidity_zones=list(market.liquidity),
            order_blocks=list(market.order_blocks),
            fair_value_gaps=list(market.fair_value_gaps),
            supply_zones=list(market.supply),
            demand_zones=list(market.demand),
            premium=market.premium,
            discount=market.discount,
            image_quality_score=market.image_quality_score,
            reconstruction_confidence=market.reconstruction_confidence,
            notes=list(market.notes),
        )

        feature_set = self._extractor.extract(chart)
        features: list[CognitiveFeature] = []
        for f in feature_set.features:
            direction = self._direction_hint(f.type, f.direction)
            features.append(
                CognitiveFeature(
                    name=f.label or f.type.replace("_", " ").title(),
                    feature_type=f.type,
                    confidence=f.confidence,
                    location=dict(f.location),
                    supporting_candles=list(f.supporting_candles),
                    relationships=list(f.relationships),
                    timeframe=market.timeframe,
                    direction_hint=direction,
                    notes=list(f.notes),
                )
            )

        missing = self._detect_missing(market)
        collection = FeatureCollection(
            timeframe=market.timeframe,
            pair=market.pair,
            features=features,
            overall_confidence=feature_set.overall_confidence,
            missing=missing,
            notes=list(market.notes),
        )
        log.info(
            "features extracted tf=%s count=%d missing=%d",
            market.timeframe,
            len(features),
            len(missing),
        )
        if self._bus:
            self._bus.publish(
                EVT_FEATURES_EXTRACTED,
                {"timeframe": market.timeframe, "count": len(features)},
            )
        return collection

    def _direction_hint(self, ftype: str, direction: str) -> str:
        bullish_types = {
            "bos",
            "bullish_order_block",
            "bullish_fvg",
            "demand_zone",
            "discount",
            "higher_high",
            "higher_low",
            "liquidity_sweep",
        }
        bearish_types = {
            "bearish_order_block",
            "bearish_fvg",
            "supply_zone",
            "premium",
            "lower_high",
            "lower_low",
        }
        if ftype == "trend":
            if direction == "Bullish":
                return "BUY"
            if direction == "Bearish":
                return "SELL"
            return "NEUTRAL"
        if ftype in bullish_types or direction == "Bullish":
            return "BUY"
        if ftype in bearish_types or direction == "Bearish":
            return "SELL"
        if ftype in {"range", "pullback"}:
            return "NEUTRAL"
        return "Unknown"

    def _detect_missing(self, market: MarketModel) -> list[str]:
        missing: list[str] = []
        if market.trend.direction == "Unknown":
            missing.append("trend")
        if market.structure_label in {"Unknown", ""}:
            missing.append("market_structure")
        if not market.liquidity:
            missing.append("liquidity")
        if not market.order_blocks:
            missing.append("order_block")
        if not market.fair_value_gaps:
            missing.append("fair_value_gap")
        if not market.swing_points:
            missing.append("swing_points")
        return missing
