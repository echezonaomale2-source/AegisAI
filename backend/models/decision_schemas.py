"""Phase 3 decision-engine schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from models.chart_schemas import ChartAnalysis


TradeDirection = Literal["BUY", "SELL", "NO TRADE"]


class ConfidenceScorecard(BaseModel):
    htf_4h_alignment: float = Field(ge=0, le=100)
    mtf_1h_alignment: float = Field(ge=0, le=100)
    ltf_15m_confirmation: float = Field(ge=0, le=100)
    liquidity: float = Field(ge=0, le=100)
    order_block: float = Field(ge=0, le=100)
    fair_value_gap: float = Field(ge=0, le=100)
    market_structure: float = Field(ge=0, le=100)
    overall: float = Field(ge=0, le=100)
    weights: dict[str, float]


class RiskPlan(BaseModel):
    entry: str = "—"
    stop_loss: str = "—"
    take_profit: str = "—"
    risk_reward: str = "—"
    target_liquidity: str = "None"
    trade_direction: TradeDirection = "NO TRADE"
    notes: list[str] = Field(default_factory=list)


class TradeDecision(BaseModel):
    pair: str
    timeframes: dict[str, str]
    analysis_4h: ChartAnalysis
    analysis_1h: ChartAnalysis
    analysis_15m: ChartAnalysis
    overall_bias: TradeDirection
    entry: str
    stop_loss: str
    take_profit: str
    risk_reward: str
    target_liquidity: str
    confidence: float = Field(ge=0, le=100)
    confidence_scorecard: ConfidenceScorecard
    explanation: str
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    status: Literal["Waiting Result"] = "Waiting Result"
    trade_id: str | None = None
    generated_at: str
