"""Engine 2 — Chart Reconstruction Engine: ChartModel → MarketModel."""

from __future__ import annotations

from cognitive.events import EVT_MARKET_REBUILT, EventBus
from cognitive.models.market import MarketModel, StructureNode
from core.logging_setup import get_logger
from core.models.chart import ChartModel

log = get_logger("cognitive.reconstruction")


class ChartReconstructionEngine:
    """
    Rebuild the visible market from ChartModel.

    Never invents missing structures — Unknown stays Unknown.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    def rebuild(self, chart: ChartModel) -> MarketModel:
        if not chart.is_usable:
            market = MarketModel(
                status="error",
                error=chart.error or "Image Quality Too Low",
                timeframe=chart.timeframe,
                pair=chart.pair,
                image_quality_score=chart.image_quality_score,
                source_chart=chart,
                notes=list(chart.notes),
            )
            if self._bus:
                self._bus.publish(EVT_MARKET_REBUILT, {"status": "error"})
            return market

        tree = self._build_structure_tree(chart)
        market = MarketModel(
            status="ok",
            timeframe=chart.timeframe,
            pair=chart.pair,
            image_quality_score=chart.image_quality_score,
            reconstruction_confidence=chart.reconstruction_confidence,
            candles=list(chart.candles),
            swing_points=list(chart.swing_points),
            trend=chart.trend,
            structure_label=chart.market_structure_label,
            structure_tree=tree,
            bos=chart.bos,
            choch=chart.choch,
            liquidity=list(chart.liquidity_zones),
            supply=list(chart.supply_zones),
            demand=list(chart.demand_zones),
            order_blocks=list(chart.order_blocks),
            fair_value_gaps=list(chart.fair_value_gaps),
            premium=chart.premium,
            discount=chart.discount,
            source_chart=chart,
            notes=list(chart.notes),
            metadata={
                "session_labels": list(chart.session_labels),
                "pair_confidence": chart.pair_confidence,
                "timeframe_confidence": chart.timeframe_confidence,
            },
        )
        log.info(
            "market rebuilt tf=%s trend=%s structure=%s nodes=%d",
            market.timeframe,
            market.trend.direction,
            market.structure_label,
            len(tree),
        )
        if self._bus:
            self._bus.publish(
                EVT_MARKET_REBUILT,
                {"timeframe": market.timeframe, "trend": market.trend.direction},
            )
        return market

    def _build_structure_tree(self, chart: ChartModel) -> list[StructureNode]:
        nodes: list[StructureNode] = []
        root_id = "trend"
        nodes.append(
            StructureNode(
                id=root_id,
                kind="trend",
                label=chart.trend.direction,
                confidence=chart.trend.confidence,
                children=[],
            )
        )
        children: list[str] = []
        if chart.bos:
            nodes.append(
                StructureNode(id="bos", kind="bos", label="Break of Structure", confidence=max(chart.trend.confidence, 70.0), parents=[root_id])
            )
            children.append("bos")
        if chart.choch:
            nodes.append(
                StructureNode(id="choch", kind="choch", label="Change of Character", confidence=max(chart.trend.confidence, 70.0), parents=[root_id])
            )
            children.append("choch")
        for i, lz in enumerate(chart.liquidity_zones):
            nid = f"liq_{i}"
            nodes.append(
                StructureNode(
                    id=nid,
                    kind=lz.kind,
                    label=lz.label or lz.kind,
                    confidence=lz.confidence,
                    parents=["bos"] if chart.bos and lz.kind == "sweep" else [root_id],
                )
            )
            children.append(nid)
        for i, ob in enumerate(chart.order_blocks):
            nid = f"ob_{i}"
            nodes.append(
                StructureNode(
                    id=nid,
                    kind=f"{ob.side}_order_block",
                    label=f"{ob.side} OB",
                    confidence=ob.confidence,
                    parents=["bos"] if chart.bos else [root_id],
                )
            )
            children.append(nid)
        for i, fvg in enumerate(chart.fair_value_gaps):
            nid = f"fvg_{i}"
            nodes.append(
                StructureNode(
                    id=nid,
                    kind=f"{fvg.side}_fvg",
                    label=f"{fvg.side} FVG",
                    confidence=fvg.confidence,
                    parents=[root_id],
                )
            )
            children.append(nid)

        # Update root children
        for n in nodes:
            if n.id == root_id:
                n.children = children
        return nodes
