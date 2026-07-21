"""Risk assessment models (Engine 7)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


RiskGrade = Literal["A", "B", "C", "D", "F"]


class RiskAssessment(BaseModel):
    entry: str = "—"
    stop_loss: str = "—"
    take_profit: str = "—"
    risk_reward: str = "—"
    distance_to_stop: float | None = None
    distance_to_target: float | None = None
    rr_numeric: float | None = None

    nearby_liquidity: str = "Unknown"
    nearby_supply: bool = False
    nearby_demand: bool = False
    session_risk: Literal["Low", "Medium", "High", "Unknown"] = "Unknown"

    confidence_adjustment: float = 0.0
    risk_grade: RiskGrade = "F"
    notes: list[str] = Field(default_factory=list)
    valid: bool = False
