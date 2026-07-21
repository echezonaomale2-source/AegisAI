"""Cognitive decision output (Engine 6)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from models.decision_schemas import TradeDecision


TradeGrade = Literal["A+", "A", "B", "C", "D", "F"]


class CognitiveDecision(BaseModel):
    """Final recommendation with full explainability trail."""

    pair: str
    recommendation: Literal["BUY", "SELL", "NO TRADE"]
    entry: str = "—"
    stop_loss: str = "—"
    take_profit: str = "—"
    risk_reward: str = "—"
    confidence: float = Field(ge=0, le=100, default=0.0)
    trade_grade: TradeGrade = "F"
    explanation: str = ""
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    gates_applied: list[str] = Field(
        default_factory=list,
        description="Decision/risk gates that shaped the recommendation",
    )

    reasoning: ReasoningReport | None = None
    risk: RiskAssessment | None = None
    legacy_decision: TradeDecision | None = Field(
        default=None,
        description="Phase 3 TradeDecision for API compatibility",
    )
    reproducible_hash: str | None = None
