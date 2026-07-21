"""ReasoningReport — holistic evaluation of all evidence (Engine 5)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cognitive.models.evidence import Evidence, EvidenceItem


class ReasoningReport(BaseModel):
    """
    Transparent reasoning over supporting, conflicting, and missing evidence.

    Reproducible: same evidence + weights → same report.
    """

    pair: str = "Unknown"
    buy_evidence_score: float = Field(ge=0, le=100, default=0.0)
    sell_evidence_score: float = Field(ge=0, le=100, default=0.0)
    neutral_score: float = Field(ge=0, le=100, default=0.0)

    supporting: list[EvidenceItem] = Field(default_factory=list)
    conflicting: list[EvidenceItem] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    supporting_structures: list[str] = Field(default_factory=list)
    conflicting_structures: list[str] = Field(default_factory=list)

    image_uncertainty: float = Field(ge=0, le=100, default=0.0)
    historical_bias: float = Field(
        default=0.0,
        description="Signed adjustment from similar historical patterns (−20..+20)",
    )

    conclusion: Literal["BUY", "SELL", "NO TRADE"] = "NO TRADE"
    confidence: float = Field(ge=0, le=100, default=0.0)

    conflicts_summary: list[str] = Field(default_factory=list)
    narrative: list[str] = Field(default_factory=list)
    explanation: str = Field(
        default="",
        description="Human-readable joined narrative for UI / audit",
    )
    gates_failed: list[str] = Field(
        default_factory=list,
        description="Named gates that forced NO TRADE (empty if trade allowed)",
    )
    evidence_snapshot: Evidence | None = None
    trace: dict[str, float] = Field(
        default_factory=dict,
        description="Traceable confidence components",
    )
