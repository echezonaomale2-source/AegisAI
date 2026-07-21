"""Smart Money and trade analysis models (reasoning layer — no BUY/SELL in SMC)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from core.models.chart import ChartModel
from core.models.features import FeatureSet


class SMCAnalysis(BaseModel):
    """Structured Smart Money reasoning for one timeframe (no trade bias)."""

    timeframe: str
    pair: str = "Unknown"
    trend: Literal["Bullish", "Bearish", "Range", "Unknown"] = "Unknown"
    market_structure: str = "Unknown"
    liquidity: str = "Unknown"
    liquidity_sweep: bool = False
    order_blocks: str = "Unknown"
    fair_value_gaps: str = "Unknown"
    supply_demand: str = "Unknown"
    premium_discount: str = "Unknown"
    bos: bool = False
    choch: bool = False
    confidence: float = Field(ge=0, le=100, default=0.0)
    reasoning: list[str] = Field(default_factory=list)
    feature_set: FeatureSet | None = None
    chart: ChartModel | None = None
    notes: list[str] = Field(default_factory=list)


class TradeAnalysis(BaseModel):
    """Multi-timeframe SMC package ready for Decision Engine."""

    pair: str
    analysis_4h: SMCAnalysis
    analysis_1h: SMCAnalysis
    analysis_15m: SMCAnalysis
    alignment: Literal["Aligned", "Conflict", "Partial", "Unknown"] = "Unknown"
    continuation: bool = False
    reversal: bool = False
    nested_structures: list[str] = Field(default_factory=list)
    relationship_notes: list[str] = Field(default_factory=list)
    relationship_confidence: float = Field(ge=0, le=100, default=0.0)
