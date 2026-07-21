"""
MarketModel — reconstructed market structure (Engine 2 output).

Built from ChartModel; contains no pixels. Downstream engines use only this
(and FeatureCollection / Evidence) — never raw images.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

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


class StructureNode(BaseModel):
    """Node in the market structure tree."""

    id: str
    kind: str
    label: str | None = None
    confidence: float = Field(ge=0, le=100, default=0.0)
    children: list[str] = Field(default_factory=list)
    parents: list[str] = Field(default_factory=list)


class MarketModel(BaseModel):
    """
    Full rebuild of the visible market from a screenshot.

    Candle sequence, swings, trend, structure tree, liquidity,
    supply/demand, order blocks, FVGs.
    """

    status: Literal["ok", "error", "unknown"] = "ok"
    error: str | None = None
    timeframe: str = "Unknown"
    pair: str = "Unknown"
    image_quality_score: float = Field(ge=0, le=100, default=0.0)
    reconstruction_confidence: float = Field(ge=0, le=100, default=0.0)

    candles: list[Candle] = Field(default_factory=list)
    swing_points: list[SwingPoint] = Field(default_factory=list)
    trend: Trend = Field(default_factory=Trend)
    structure_label: str = "Unknown"
    structure_tree: list[StructureNode] = Field(default_factory=list)
    bos: bool = False
    choch: bool = False

    liquidity: list[LiquidityZone] = Field(default_factory=list)
    supply: list[SupplyZone] = Field(default_factory=list)
    demand: list[DemandZone] = Field(default_factory=list)
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    fair_value_gaps: list[FairValueGap] = Field(default_factory=list)
    premium: Literal["Yes", "No", "Unknown"] = "Unknown"
    discount: Literal["Yes", "No", "Unknown"] = "Unknown"

    source_chart: ChartModel | None = Field(
        default=None,
        description="Optional back-reference to ChartModel (no pixels)",
    )
    notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def is_usable(self) -> bool:
        return self.status == "ok" and len(self.candles) >= 5
