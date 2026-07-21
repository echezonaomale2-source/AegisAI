"""Evaluation data models and metric schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


HealthGrade = Literal["Excellent", "Good", "Improving", "Needs Review", "Critical", "Unknown"]


class VisionMetrics(BaseModel):
    images_accepted: int = 0
    images_rejected: int = 0
    avg_detection_confidence: float | None = None
    timeframe_detections: int = 0
    pair_detections: int = 0
    structure_detections: int = 0
    unknown_detections: int = 0
    false_detections_verified: int = 0
    accept_rate: float | None = None


class FeatureMetrics(BaseModel):
    trend_detection_rate: float | None = None
    bos_detection_rate: float | None = None
    choch_detection_rate: float | None = None
    liquidity_detection_rate: float | None = None
    order_block_detection_rate: float | None = None
    fvg_detection_rate: float | None = None
    supply_detection_rate: float | None = None
    demand_detection_rate: float | None = None
    unknown_rate: float | None = None
    total_feature_events: int = 0


class DecisionMetrics(BaseModel):
    buy_recommendations: int = 0
    sell_recommendations: int = 0
    no_trade_recommendations: int = 0
    average_confidence: float | None = None
    confidence_distribution: dict[str, int] = Field(default_factory=dict)
    average_risk_reward: float | None = None
    total_decisions: int = 0


class CalibrationMetrics(BaseModel):
    sample_count: int = 0
    global_gap: float = 0.0
    adjustment_factor: float = 1.0
    expected_calibration_error: float | None = None
    bins: list[dict[str, Any]] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class TradeReviewMetrics(BaseModel):
    winning_analyses: int = 0
    losing_analyses: int = 0
    average_review_score: float | None = None
    avg_entry_quality: float | None = None
    avg_stop_loss_quality: float | None = None
    avg_take_profit_quality: float | None = None
    avg_htf_alignment_quality: float | None = None
    completed_reviews: int = 0
    decision_quality_distribution: dict[str, int] = Field(default_factory=dict)


class LearningMetrics(BaseModel):
    pattern_statistics_updated: int = 0
    confidence_adjustments_made: int = 0
    lessons_generated: int = 0
    memory_growth: int = 0
    similarity_searches: int = 0
    effectiveness_score: float | None = None
    notes: list[str] = Field(default_factory=list)


class KnowledgeMetrics(BaseModel):
    concepts_validated: int = 0
    concepts_rejected: int = 0
    unknown_rate: float | None = None
    knowledge_version: str = "1.0"


class EvidenceMetrics(BaseModel):
    avg_buy_weight: float | None = None
    avg_sell_weight: float | None = None
    avg_neutral_weight: float | None = None
    consistency_score: float | None = None


class ModuleHealth(BaseModel):
    module: str
    grade: HealthGrade = "Unknown"
    score: float = Field(ge=0, le=100, default=0.0)
    notes: list[str] = Field(default_factory=list)


class SystemHealthReport(BaseModel):
    overall_grade: HealthGrade = "Unknown"
    overall_score: float = 0.0
    modules: list[ModuleHealth] = Field(default_factory=list)
    generated_at: str | None = None


class DecisionPathLog(BaseModel):
    """Full decision path for debugging — immutable once stored."""

    log_id: str
    trade_id: str | None = None
    timestamp: str
    input_summary: dict[str, Any] = Field(default_factory=dict)
    validated_concepts: list[str] = Field(default_factory=list)
    evidence_summary: dict[str, Any] = Field(default_factory=dict)
    reasoning_summary: dict[str, Any] = Field(default_factory=dict)
    decision: str = "NO TRADE"
    confidence: float = 0.0
    knowledge_version: str | None = None
    outcome: str | None = None
    review_scores: dict[str, Any] | None = None
    variant_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class QualityGateResult(BaseModel):
    accepted: bool
    gate_name: str
    baseline_score: float
    candidate_score: float
    delta: float
    min_improvement: float
    reason: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ABTestRecord(BaseModel):
    test_id: str
    name: str
    baseline_variant: str
    candidate_variant: str
    status: Literal["running", "completed", "rejected", "accepted"] = "running"
    baseline_metrics: dict[str, Any] = Field(default_factory=dict)
    candidate_metrics: dict[str, Any] = Field(default_factory=dict)
    gate_result: QualityGateResult | None = None
    created_at: str | None = None
    completed_at: str | None = None


class EvaluationReport(BaseModel):
    report_id: str
    created_at: str
    vision: VisionMetrics = Field(default_factory=VisionMetrics)
    features: FeatureMetrics = Field(default_factory=FeatureMetrics)
    knowledge: KnowledgeMetrics = Field(default_factory=KnowledgeMetrics)
    evidence: EvidenceMetrics = Field(default_factory=EvidenceMetrics)
    decisions: DecisionMetrics = Field(default_factory=DecisionMetrics)
    calibration: CalibrationMetrics = Field(default_factory=CalibrationMetrics)
    trade_reviews: TradeReviewMetrics = Field(default_factory=TradeReviewMetrics)
    learning: LearningMetrics = Field(default_factory=LearningMetrics)
    health: SystemHealthReport = Field(default_factory=SystemHealthReport)
    dashboard: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class EvaluationDashboard(BaseModel):
    total_analyses: int = 0
    completed_reviews: int = 0
    current_calibration_quality: str = "Unknown"
    most_reliable_feature: str | None = None
    least_reliable_feature: str | None = None
    common_no_trade_reasons: list[str] = Field(default_factory=list)
    recent_lessons: list[str] = Field(default_factory=list)
    overall_system_health: SystemHealthReport | None = None
    latest_report_id: str | None = None
    decision_path_log_count: int = 0
