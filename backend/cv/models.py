"""Phase 5 Computer Vision data models — visual understanding only (no trade bias)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


FeatureType = Literal[
    "swing_high",
    "swing_low",
    "higher_high",
    "higher_low",
    "lower_high",
    "lower_low",
    "trend",
    "range",
    "impulse",
    "pullback",
    "bos",
    "choch",
    "liquidity",
    "liquidity_sweep",
    "equal_highs",
    "equal_lows",
    "bullish_order_block",
    "bearish_order_block",
    "bullish_fvg",
    "bearish_fvg",
    "supply_zone",
    "demand_zone",
    "premium",
    "discount",
    "mitigation",
    "rejection",
    "unknown",
]


class CandleOHLC(BaseModel):
    index: int
    open: float
    high: float
    low: float
    close: float
    bullish: bool
    body_size: float
    upper_wick: float
    lower_wick: float
    relative_position: float = Field(
        description="0–1 position across the visible chart (left→right)"
    )
    confidence: float = Field(ge=0, le=100, default=70.0)


class FeatureObject(BaseModel):
    id: str
    type: FeatureType
    location: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=100)
    supporting_candles: list[int] = Field(default_factory=list)
    relationships: list[str] = Field(
        default_factory=list,
        description="IDs of related feature nodes",
    )
    label: str | None = None
    notes: list[str] = Field(default_factory=list)


class FeatureGraphNode(BaseModel):
    id: str
    type: FeatureType
    confidence: float
    label: str | None = None
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)


class FeatureGraph(BaseModel):
    root_ids: list[str] = Field(default_factory=list)
    nodes: dict[str, FeatureGraphNode] = Field(default_factory=dict)
    edges: list[dict[str, str]] = Field(default_factory=list)

    def as_tree_dict(self) -> dict[str, Any]:
        def walk(node_id: str) -> dict[str, Any]:
            node = self.nodes[node_id]
            return {
                "id": node.id,
                "type": node.type,
                "label": node.label,
                "confidence": node.confidence,
                "children": [walk(cid) for cid in node.children if cid in self.nodes],
            }

        return {"roots": [walk(rid) for rid in self.root_ids if rid in self.nodes]}


class ChartMeta(BaseModel):
    pair: str = "Unknown"
    timeframe: str = "Unknown"
    detected_timeframe_label: str | None = None
    price_scale: dict[str, Any] | None = None
    chart_bounds: dict[str, int] | None = None
    session_labels: list[str] = Field(default_factory=list)
    pair_confidence: float = 0.0
    timeframe_confidence: float = 0.0
    roi_confidence: float = 0.0


class VisionChartResult(BaseModel):
    """Complete visual understanding of one chart — no BUY/SELL."""

    status: Literal["ok", "error"] = "ok"
    error: str | None = None
    image_path: str | None = None
    quality_score: float = 0.0
    meta: ChartMeta = Field(default_factory=ChartMeta)
    candles: list[CandleOHLC] = Field(default_factory=list)
    features: list[FeatureObject] = Field(default_factory=list)
    feature_graph: FeatureGraph = Field(default_factory=FeatureGraph)
    summary: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    cache_hit: bool = False


class MTFRelationship(BaseModel):
    alignment: Literal["Aligned", "Conflict", "Partial", "Unknown"] = "Unknown"
    continuation: bool = False
    reversal: bool = False
    nested_structures: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    confidence: float = 0.0


class VisionMultiResult(BaseModel):
    status: Literal["ok", "partial", "error"] = "ok"
    chart_4h: VisionChartResult
    chart_1h: VisionChartResult
    chart_15m: VisionChartResult
    relationship: MTFRelationship
    notes: list[str] = Field(default_factory=list)
