"""Structured feature objects extracted from ChartModel."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


FeatureType = Literal[
    "trend",
    "range",
    "swing_high",
    "swing_low",
    "higher_high",
    "higher_low",
    "lower_high",
    "lower_low",
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


class Feature(BaseModel):
    """Atomic market feature with confidence and relationships."""

    id: str
    type: FeatureType
    label: str | None = None
    detected: bool = True
    direction: Literal["Bullish", "Bearish", "Neutral", "Unknown"] = "Unknown"
    confidence: float = Field(ge=0, le=100, default=0.0)
    location: dict[str, Any] = Field(default_factory=dict)
    supporting_candles: list[int] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class FeatureSet(BaseModel):
    """All features for one reconstructed chart."""

    timeframe: str = "Unknown"
    pair: str = "Unknown"
    features: list[Feature] = Field(default_factory=list)
    graph: dict[str, Any] = Field(
        default_factory=dict,
        description="Nested structure graph for Decision Engine consumption",
    )
    overall_confidence: float = Field(ge=0, le=100, default=0.0)
    unknown_count: int = 0
    notes: list[str] = Field(default_factory=list)

    def get(self, feature_type: str) -> list[Feature]:
        return [f for f in self.features if f.type == feature_type]

    def primary(self, feature_type: str) -> Feature | None:
        matches = self.get(feature_type)
        if not matches:
            return None
        return max(matches, key=lambda f: f.confidence)
