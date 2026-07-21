"""Permanent memory and learning data models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class Lesson(BaseModel):
    id: str | None = None
    trade_id: str | None = None
    text: str
    category: str = "general"
    created_at: str | None = None


class PatternMemory(BaseModel):
    pattern_key: str
    name: str | None = None
    trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float | None = None
    avg_rr: float | None = None
    fingerprint_bits: list[int] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TradeMemory(BaseModel):
    """Permanent record of a trade lifecycle — history is never overwritten."""

    trade_id: str
    pair: str
    timestamp: str | None = None
    chart_4h_path: str | None = None
    chart_1h_path: str | None = None
    chart_15m_path: str | None = None
    reconstructed_4h: dict[str, Any] | None = None
    reconstructed_1h: dict[str, Any] | None = None
    reconstructed_15m: dict[str, Any] | None = None
    features: dict[str, Any] | None = None
    analysis: dict[str, Any] | None = None
    decision: Literal["BUY", "SELL", "NO TRADE"] | None = None
    entry: str | None = None
    stop_loss: str | None = None
    take_profit: str | None = None
    confidence: float | None = None
    explanation: str | None = None
    lessons: list[Lesson] = Field(default_factory=list)
    outcome: str | None = None
    outcome_notes: str | None = None
    fingerprint_hash: str | None = None
    fingerprint_bits: list[int] = Field(default_factory=list)
    status: str = "Waiting Result"
