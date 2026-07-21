"""
Chart Reconstruction — convert vision output into ChartModel.

Downstream AI must never access raw images; only ChartModel.
"""

from __future__ import annotations

from pathlib import Path

from core.logging_setup import get_logger
from core.models.chart import (
    Candle,
    ChartModel,
    DemandZone,
    FairValueGap,
    LiquidityZone,
    OrderBlock,
    SupplyZone,
    SwingPoint,
    Trend,
)
from cv.models import FeatureObject, VisionChartResult
from cv.vision_engine import VisionEngine

log = get_logger("reconstruction")


class ChartReconstructor:
    """
    Heart of the system: screenshot → ChartModel.

    Uses VisionEngine for pixel understanding, then strips all image data
    into a typed reconstructed model.
    """

    def __init__(self, vision_engine: VisionEngine | None = None) -> None:
        self._vision = vision_engine or VisionEngine(use_cache=True)

    def reconstruct(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
        pair: str | None = None,
    ) -> ChartModel:
        result = self._vision.analyze_chart(
            path, expected_timeframe=expected_timeframe, pair=pair
        )
        model = self.from_vision_result(result)
        log.info(
            "reconstructed chart path=%s status=%s candles=%d quality=%.1f",
            path,
            model.status,
            len(model.candles),
            model.image_quality_score,
        )
        return model

    def from_vision_result(self, result: VisionChartResult) -> ChartModel:
        if result.status != "ok":
            return ChartModel(
                status="error",
                error=result.error or "Image Quality Too Low",
                pair=result.meta.pair,
                timeframe=result.meta.timeframe,
                detected_timeframe_label=result.meta.detected_timeframe_label,
                image_quality_score=result.quality_score,
                source_image_path=result.image_path,
                notes=list(result.notes),
                cache_hit=result.cache_hit,
            )

        candles = [
            Candle(
                index=c.index,
                open=c.open,
                high=c.high,
                low=c.low,
                close=c.close,
                bullish=c.bullish,
                body_size=c.body_size,
                upper_wick=c.upper_wick,
                lower_wick=c.lower_wick,
                relative_position=c.relative_position,
                confidence=c.confidence,
            )
            for c in result.candles
        ]

        features = result.features
        summary = result.summary or {}

        trend_raw = summary.get("trend", "Unknown")
        trend_dir = trend_raw if trend_raw in {"Bullish", "Bearish", "Range"} else "Unknown"
        trend_conf = _feature_conf(features, "trend", _feature_conf(features, "range", 0.0))

        structure_label = "Unknown"
        for f in features:
            if f.id == "structure_primary" and f.label:
                structure_label = f.label
                break

        swing_points = _swings_from_features(features, candles)
        liquidity = _liquidity_from_features(features)
        order_blocks = _order_blocks_from_features(features)
        fvgs = _fvgs_from_features(features)
        supply = _zones_from_features(features, "supply_zone", SupplyZone)
        demand = _zones_from_features(features, "demand_zone", DemandZone)

        premium: str = "Unknown"
        discount: str = "Unknown"
        if any(f.type == "premium" for f in features):
            premium, discount = "Yes", "No"
        elif any(f.type == "discount" for f in features):
            premium, discount = "No", "Yes"

        recon_conf = _mean(
            [
                result.quality_score,
                trend_conf,
                result.meta.pair_confidence,
                result.meta.timeframe_confidence,
            ]
        )

        return ChartModel(
            status="ok",
            pair=result.meta.pair,
            timeframe=result.meta.timeframe,
            detected_timeframe_label=result.meta.detected_timeframe_label,
            price_scale=result.meta.price_scale,
            chart_bounds=result.meta.chart_bounds,
            session_labels=list(result.meta.session_labels),
            image_quality_score=result.quality_score,
            pair_confidence=result.meta.pair_confidence,
            timeframe_confidence=result.meta.timeframe_confidence,
            candles=candles,
            swing_points=swing_points,
            trend=Trend(
                direction=trend_dir,  # type: ignore[arg-type]
                confidence=trend_conf,
                impulse_move=any(f.type == "impulse" for f in features),
                pullback=any(f.type == "pullback" for f in features),
            ),
            market_structure_label=structure_label,
            bos=bool(summary.get("bos")),
            choch=bool(summary.get("choch")),
            liquidity_zones=liquidity,
            order_blocks=order_blocks,
            fair_value_gaps=fvgs,
            supply_zones=supply,  # type: ignore[arg-type]
            demand_zones=demand,  # type: ignore[arg-type]
            premium=premium,  # type: ignore[arg-type]
            discount=discount,  # type: ignore[arg-type]
            strong_rejection=any(
                f.type == "rejection" and f.label == "Strong Rejection" for f in features
            ),
            weak_rejection=any(
                f.type == "rejection" and f.label == "Weak Rejection" for f in features
            ),
            source_image_path=result.image_path,
            reconstruction_confidence=recon_conf,
            notes=list(result.notes),
            cache_hit=result.cache_hit,
        )


def _feature_conf(features: list[FeatureObject], ftype: str, default: float = 0.0) -> float:
    for f in features:
        if f.type == ftype and f.confidence > 0:
            return float(f.confidence)
    return default


def _mean(values: list[float]) -> float:
    usable = [v for v in values if v is not None]
    if not usable:
        return 0.0
    return max(0.0, min(100.0, sum(usable) / len(usable)))


def _swings_from_features(
    features: list[FeatureObject], candles: list[Candle]
) -> list[SwingPoint]:
    points: list[SwingPoint] = []
    for f in features:
        if f.type not in {"swing_high", "swing_low", "higher_high", "higher_low", "lower_high", "lower_low"}:
            continue
        idx = f.supporting_candles[0] if f.supporting_candles else f.location.get("index", 0)
        try:
            index = int(idx)
        except (TypeError, ValueError):
            index = 0
        price = f.location.get("price")
        if price is None and 0 <= index < len(candles):
            price = candles[index].high if "high" in f.type else candles[index].low
        kind = "high" if "high" in f.type else "low"
        structure = f.location.get("structure_label")
        if structure is None and f.type in {"higher_high", "higher_low", "lower_high", "lower_low"}:
            structure = {
                "higher_high": "HH",
                "higher_low": "HL",
                "lower_high": "LH",
                "lower_low": "LL",
            }[f.type]
        points.append(
            SwingPoint(
                index=index,
                price=float(price) if price is not None else 0.0,
                kind=kind,  # type: ignore[arg-type]
                structure_label=structure,
                confidence=f.confidence,
            )
        )
    return points


def _liquidity_from_features(features: list[FeatureObject]) -> list[LiquidityZone]:
    zones: list[LiquidityZone] = []
    for f in features:
        if f.type not in {"liquidity", "liquidity_sweep", "equal_highs", "equal_lows"}:
            continue
        kind = "unknown"
        if f.type == "liquidity_sweep":
            kind = "sweep"
        elif f.type == "equal_highs":
            kind = "equal_highs"
        elif f.type == "equal_lows":
            kind = "equal_lows"
        elif f.location.get("kind") == "internal":
            kind = "internal"
        elif f.location.get("kind") == "external":
            kind = "external"
        elif f.label and "Above" in f.label:
            kind = "buy_side"
        elif f.label and "Below" in f.label:
            kind = "sell_side"
        elif f.label and "Internal" in f.label:
            kind = "internal"
        elif f.label and "External" in f.label:
            kind = "external"
        zones.append(
            LiquidityZone(
                id=f.id,
                kind=kind,  # type: ignore[arg-type]
                price=f.location.get("price"),
                swept=f.type == "liquidity_sweep",
                confidence=f.confidence,
                supporting_candles=list(f.supporting_candles),
                label=f.label,
            )
        )
    return zones


def _order_blocks_from_features(features: list[FeatureObject]) -> list[OrderBlock]:
    blocks: list[OrderBlock] = []
    for f in features:
        if f.type == "bullish_order_block":
            side = "bullish"
        elif f.type == "bearish_order_block":
            side = "bearish"
        else:
            continue
        blocks.append(
            OrderBlock(
                id=f.id,
                side=side,  # type: ignore[arg-type]
                high=f.location.get("high"),
                low=f.location.get("low"),
                mitigated=bool(f.location.get("mitigated", False)),
                confidence=f.confidence,
                supporting_candles=list(f.supporting_candles),
            )
        )
    return blocks


def _fvgs_from_features(features: list[FeatureObject]) -> list[FairValueGap]:
    gaps: list[FairValueGap] = []
    for f in features:
        if f.type == "bullish_fvg":
            side = "bullish"
        elif f.type == "bearish_fvg":
            side = "bearish"
        else:
            continue
        gaps.append(
            FairValueGap(
                id=f.id,
                side=side,  # type: ignore[arg-type]
                high=f.location.get("high"),
                low=f.location.get("low"),
                filled=bool(f.location.get("filled", False)),
                confidence=f.confidence,
                supporting_candles=list(f.supporting_candles),
            )
        )
    return gaps


def _zones_from_features(features: list[FeatureObject], ftype: str, cls: type):
    out = []
    for f in features:
        if f.type != ftype:
            continue
        out.append(
            cls(
                id=f.id,
                high=f.location.get("high"),
                low=f.location.get("low"),
                confidence=f.confidence,
                supporting_candles=list(f.supporting_candles),
            )
        )
    return out
