"""Research-grade typed models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DecisionQuality = Literal["Excellent", "Good", "Acceptable", "Borderline", "Avoid"]


class ResearchScorecard(BaseModel):
    """Trade review scorecard — analysis quality, not P&L."""

    higher_timeframe_alignment: float = Field(ge=0, le=100, default=0)
    entry_quality: float = Field(ge=0, le=100, default=0)
    stop_loss_placement: float = Field(ge=0, le=100, default=0)
    take_profit_placement: float = Field(ge=0, le=100, default=0)
    market_structure_detection: float = Field(ge=0, le=100, default=0)
    liquidity_detection: float = Field(ge=0, le=100, default=0)
    order_block_quality: float = Field(ge=0, le=100, default=0)
    fvg_quality: float = Field(ge=0, le=100, default=0)
    confidence_calibration: float = Field(ge=0, le=100, default=0)
    overall_analysis_quality: float = Field(ge=0, le=100, default=0)


class ReviewReport(BaseModel):
    trade_id: str
    outcome: str
    htf_bias_correct: bool | None = None
    m15_confirmation_valid: bool | None = None
    liquidity_identified_correctly: bool | None = None
    order_block_respected: bool | None = None
    fvg_meaningful: bool | None = None
    confidence_appropriate: bool | None = None
    should_have_been_no_trade: bool = False
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    scorecard: ResearchScorecard = Field(default_factory=ResearchScorecard)
    decision_quality: DecisionQuality = "Acceptable"
    questions: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    lessons: list[str] = Field(default_factory=list)
    cognitive_hash: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class CalibrationBin(BaseModel):
    """Predicted confidence band vs realized success."""

    bin_label: str
    min_confidence: float
    max_confidence: float
    predictions: int = 0
    successes: int = 0
    realized_rate: float | None = None
    predicted_midpoint: float = 0.0
    calibration_gap: float | None = None  # predicted - realized


class CalibrationState(BaseModel):
    bins: list[CalibrationBin] = Field(default_factory=list)
    global_gap: float = 0.0  # positive = overconfident
    sample_count: int = 0
    adjustment_factor: float = 1.0  # multiply future confidence
    expected_calibration_error: float | None = None
    last_updated: str | None = None
    notes: list[str] = Field(default_factory=list)


class PatternRecord(BaseModel):
    pattern_id: str
    feature_combination: list[str] = Field(default_factory=list)
    occurrences: int = 0
    wins: int = 0
    losses: int = 0
    no_trade_recommendations: int = 0
    average_confidence: float | None = None
    average_risk_reward: float | None = None
    average_holding_time_hours: float | None = None
    last_updated: str | None = None
    reliability_score: float | None = None


class SelfCheckResult(BaseModel):
    passed: bool
    force_no_trade: bool = False
    checks: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    summary: str = ""


class ResearchDashboard(BaseModel):
    total_analyses: int = 0
    trades_awaiting_results: int = 0
    completed_reviews: int = 0
    current_confidence_calibration: CalibrationState | None = None
    most_reliable_feature_combination: PatternRecord | None = None
    least_reliable_feature_combination: PatternRecord | None = None
    most_common_reason_for_losing_trades: str | None = None
    most_common_reason_for_no_trade: str | None = None
    recent_lessons: list[str] = Field(default_factory=list)
    decision_quality_distribution: dict[str, int] = Field(default_factory=dict)
    # Step 9 — embedded snapshots (also available via dedicated endpoints)
    top_patterns: list[PatternRecord] = Field(default_factory=list)
    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    learning_snapshot: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
