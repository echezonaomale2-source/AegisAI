"""Evidence models — evaluated features with direction, strength, and weight."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cognitive.models.features import CognitiveFeature


EvidenceDirection = Literal["BUY", "SELL", "NEUTRAL"]
EvidenceStrength = Literal["Very Strong", "Strong", "Medium", "Weak", "Very Weak"]


class EvidenceItem(BaseModel):
    """Single piece of evaluated market evidence."""

    id: str
    name: str
    feature_type: str
    direction: EvidenceDirection
    strength: EvidenceStrength
    weight: float = Field(ge=0, description="Relative influence on reasoning")
    confidence: float = Field(ge=0, le=100)
    timeframe: str = "Unknown"
    supporting_candles: list[int] = Field(default_factory=list)
    supporting_structures: list[str] = Field(
        default_factory=list,
        description="Related structure labels that back this item",
    )
    source_feature: CognitiveFeature | None = None
    rationale: str = ""
    trace_id: str = Field(
        default="",
        description="Stable id for reproducibility / audit trail",
    )


class Evidence(BaseModel):
    """Structured evidence list for one or more timeframes."""

    items: list[EvidenceItem] = Field(default_factory=list)
    buy_weight: float = 0.0
    sell_weight: float = 0.0
    neutral_weight: float = 0.0
    dominant_direction: EvidenceDirection = "NEUTRAL"
    image_uncertainty: float = Field(
        ge=0,
        le=100,
        default=0.0,
        description="100 = fully uncertain image quality",
    )
    supporting_structures: list[str] = Field(
        default_factory=list,
        description="Structures aligned with the dominant directional weight",
    )
    conflicting_structures: list[str] = Field(
        default_factory=list,
        description="Structures opposing the dominant directional weight",
    )
    missing_evidence: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @property
    def total_directional_weight(self) -> float:
        return self.buy_weight + self.sell_weight


class EvidenceReport(BaseModel):
    """Explainable evidence report for one timeframe (or a multi-TF rollup)."""

    timeframe: str = "Unknown"
    pair: str = "Unknown"
    buy_weight: float = 0.0
    sell_weight: float = 0.0
    neutral_weight: float = 0.0
    dominant_direction: EvidenceDirection = "NEUTRAL"
    item_count: int = 0
    items: list[EvidenceItem] = Field(default_factory=list)
    supporting_structures: list[str] = Field(default_factory=list)
    conflicting_structures: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    image_uncertainty: float = 0.0
    notes: list[str] = Field(default_factory=list)
    summary: str = ""
