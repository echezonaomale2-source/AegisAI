"""FeatureCollection — structured features from MarketModel (Engine 3)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class CognitiveFeature(BaseModel):
    name: str
    feature_type: str
    confidence: float = Field(ge=0, le=100, default=0.0)
    location: dict[str, Any] = Field(default_factory=dict)
    supporting_candles: list[int] = Field(default_factory=list)
    relationships: list[str] = Field(default_factory=list)
    timeframe: str = "Unknown"
    direction_hint: Literal["BUY", "SELL", "NEUTRAL", "Unknown"] = "Unknown"
    notes: list[str] = Field(default_factory=list)


class FeatureCollection(BaseModel):
    timeframe: str = "Unknown"
    pair: str = "Unknown"
    features: list[CognitiveFeature] = Field(default_factory=list)
    overall_confidence: float = Field(ge=0, le=100, default=0.0)
    missing: list[str] = Field(
        default_factory=list,
        description="Expected structures that could not be detected (Unknown — never invented)",
    )
    notes: list[str] = Field(default_factory=list)

    def by_type(self, feature_type: str) -> list[CognitiveFeature]:
        return [f for f in self.features if f.feature_type == feature_type]
