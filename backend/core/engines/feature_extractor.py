"""Feature extraction from ChartModel (image-free)."""

from __future__ import annotations

from core.logging_setup import get_logger
from core.models.chart import ChartModel
from core.models.features import Feature, FeatureSet
from cv.structure_graph_builder import StructureGraphBuilder
from cv.models import FeatureObject

log = get_logger("features")


class FeatureExtractor:
    """Convert reconstructed ChartModel into structured Feature objects."""

    def __init__(self) -> None:
        self._graph = StructureGraphBuilder()

    def extract(self, chart: ChartModel) -> FeatureSet:
        if not chart.is_usable:
            return FeatureSet(
                timeframe=chart.timeframe,
                pair=chart.pair,
                features=[
                    Feature(
                        id="unknown_chart",
                        type="unknown",
                        label="Unknown",
                        detected=False,
                        confidence=0.0,
                        notes=[chart.error or "Chart not usable"],
                    )
                ],
                unknown_count=1,
                notes=list(chart.notes),
            )

        features: list[Feature] = []

        features.append(
            Feature(
                id="trend",
                type="trend" if chart.trend.direction != "Range" else "range",
                label=chart.trend.direction,
                direction=chart.trend.direction if chart.trend.direction != "Range" else "Neutral",  # type: ignore[arg-type]
                confidence=chart.trend.confidence,
                detected=chart.trend.direction != "Unknown",
            )
        )

        if chart.trend.impulse_move:
            features.append(
                Feature(id="impulse", type="impulse", label="Impulse", confidence=chart.trend.confidence)
            )
        if chart.trend.pullback:
            features.append(
                Feature(id="pullback", type="pullback", label="Pullback", confidence=chart.trend.confidence)
            )

        for i, sp in enumerate(chart.swing_points):
            ftype = "swing_high" if sp.kind == "high" else "swing_low"
            if sp.structure_label == "HH":
                ftype = "higher_high"
            elif sp.structure_label == "HL":
                ftype = "higher_low"
            elif sp.structure_label == "LH":
                ftype = "lower_high"
            elif sp.structure_label == "LL":
                ftype = "lower_low"
            features.append(
                Feature(
                    id=f"swing_{i}",
                    type=ftype,  # type: ignore[arg-type]
                    label=sp.structure_label or ftype,
                    confidence=sp.confidence,
                    location={"index": sp.index, "price": sp.price},
                    supporting_candles=[sp.index],
                )
            )

        if chart.bos:
            features.append(
                Feature(
                    id="bos",
                    type="bos",
                    label="Break of Structure",
                    direction=chart.trend.direction if chart.trend.direction in {"Bullish", "Bearish"} else "Unknown",  # type: ignore[arg-type]
                    confidence=max(chart.trend.confidence, 70.0),
                )
            )
        if chart.choch:
            features.append(
                Feature(
                    id="choch",
                    type="choch",
                    label="Change of Character",
                    confidence=max(chart.trend.confidence, 70.0),
                )
            )

        for lz in chart.liquidity_zones:
            ftype = "liquidity"
            if lz.kind == "sweep":
                ftype = "liquidity_sweep"
            elif lz.kind == "equal_highs":
                ftype = "equal_highs"
            elif lz.kind == "equal_lows":
                ftype = "equal_lows"
            features.append(
                Feature(
                    id=lz.id,
                    type=ftype,  # type: ignore[arg-type]
                    label=lz.label or lz.kind,
                    confidence=lz.confidence,
                    location={"price": lz.price, "swept": lz.swept},
                    supporting_candles=list(lz.supporting_candles),
                )
            )

        for ob in chart.order_blocks:
            ftype = "bullish_order_block" if ob.side == "bullish" else "bearish_order_block"
            if ob.side == "unknown":
                ftype = "unknown"
            features.append(
                Feature(
                    id=ob.id,
                    type=ftype,  # type: ignore[arg-type]
                    label=ob.side.title() + " Order Block" if ob.side != "unknown" else "Unknown",
                    direction="Bullish" if ob.side == "bullish" else "Bearish" if ob.side == "bearish" else "Unknown",
                    confidence=ob.confidence,
                    location={"high": ob.high, "low": ob.low, "mitigated": ob.mitigated},
                    supporting_candles=list(ob.supporting_candles),
                )
            )

        for fvg in chart.fair_value_gaps:
            ftype = "bullish_fvg" if fvg.side == "bullish" else "bearish_fvg"
            if fvg.side == "unknown":
                ftype = "unknown"
            features.append(
                Feature(
                    id=fvg.id,
                    type=ftype,  # type: ignore[arg-type]
                    label=fvg.side.title() + " FVG" if fvg.side != "unknown" else "Unknown",
                    direction="Bullish" if fvg.side == "bullish" else "Bearish" if fvg.side == "bearish" else "Unknown",
                    confidence=fvg.confidence,
                    location={"high": fvg.high, "low": fvg.low, "filled": fvg.filled},
                    supporting_candles=list(fvg.supporting_candles),
                )
            )

        for z in chart.supply_zones:
            features.append(
                Feature(
                    id=z.id,
                    type="supply_zone",
                    label="Supply",
                    direction="Bearish",
                    confidence=z.confidence,
                    location={"high": z.high, "low": z.low},
                    supporting_candles=list(z.supporting_candles),
                )
            )
        for z in chart.demand_zones:
            features.append(
                Feature(
                    id=z.id,
                    type="demand_zone",
                    label="Demand",
                    direction="Bullish",
                    confidence=z.confidence,
                    location={"high": z.high, "low": z.low},
                    supporting_candles=list(z.supporting_candles),
                )
            )

        if chart.premium == "Yes":
            features.append(Feature(id="premium", type="premium", label="Premium", confidence=70.0))
        if chart.discount == "Yes":
            features.append(Feature(id="discount", type="discount", label="Discount", confidence=70.0))

        if chart.strong_rejection:
            features.append(
                Feature(id="rejection_strong", type="rejection", label="Strong Rejection", confidence=75.0)
            )
        elif chart.weak_rejection:
            features.append(
                Feature(id="rejection_weak", type="rejection", label="Weak Rejection", confidence=55.0)
            )

        # Build graph via existing StructureGraphBuilder using FeatureObject bridge.
        legacy = [
            FeatureObject(
                id=f.id,
                type=f.type,  # type: ignore[arg-type]
                location=f.location,
                confidence=f.confidence,
                supporting_candles=f.supporting_candles,
                relationships=f.relationships,
                label=f.label,
                notes=f.notes,
            )
            for f in features
            if f.type != "unknown"
        ]
        graph = self._graph.build(legacy)

        confidences = [f.confidence for f in features if f.detected and f.type != "unknown"]
        overall = sum(confidences) / len(confidences) if confidences else 0.0
        unknown_count = sum(1 for f in features if f.type == "unknown" or not f.detected)

        log.info(
            "extracted %d features pair=%s tf=%s overall=%.1f",
            len(features),
            chart.pair,
            chart.timeframe,
            overall,
        )
        return FeatureSet(
            timeframe=chart.timeframe,
            pair=chart.pair,
            features=features,
            graph=graph.as_tree_dict(),
            overall_confidence=overall,
            unknown_count=unknown_count,
            notes=list(chart.notes),
        )
