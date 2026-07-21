"""AI Brain data models — recommendation output and reason traces."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from verification.models import VerificationSummary


TradeBias = Literal["BUY", "SELL", "NO TRADE"]
TradeGrade = Literal["A+", "A", "B", "C", "D", "F"]
HistoricalStrength = Literal["Strong", "Moderate", "Weak", "None", "Unknown"]


class HistoricalSupport(BaseModel):
    pattern_similarity: float | None = Field(default=None, ge=0, le=100)
    previous_similar_analyses: int = 0
    wins: int = 0
    losses: int = 0
    historical_support: HistoricalStrength = "Unknown"
    influence_on_confidence: float = 0.0  # signed delta applied
    notes: list[str] = Field(default_factory=list)


class CompletenessReport(BaseModel):
    complete: bool
    missing_critical: list[str] = Field(default_factory=list)
    missing_optional: list[str] = Field(default_factory=list)
    poor_image_quality: bool = False
    request_better_screenshot: bool = False
    notes: list[str] = Field(default_factory=list)


class ConflictReport(BaseModel):
    has_conflicts: bool
    htf_disagreement: bool = False
    conflicts: list[str] = Field(default_factory=list)
    severity: Literal["none", "low", "medium", "high"] = "none"


class BrainSelfCheck(BaseModel):
    evidence_complete: bool
    evidence_consistent: bool
    confidence_justified: bool
    professional_setup: bool
    prefer_no_trade: bool
    passed: bool
    warnings: list[str] = Field(default_factory=list)


class ReasonTraceStep(BaseModel):
    engine: str
    action: str
    detail: str = ""


class ReasonTrace(BaseModel):
    """Complete auditable reasoning path for one recommendation."""

    trace_id: str
    steps: list[ReasonTraceStep] = Field(default_factory=list)
    final_action: str = ""
    deterministic_hash: str | None = None

    def add(self, engine: str, action: str, detail: str = "") -> None:
        self.steps.append(ReasonTraceStep(engine=engine, action=action, detail=detail))


class EngineBundle(BaseModel):
    """Validated information gathered from all engines — no raw images."""

    pair: str = "Unknown"
    timeframes: dict[str, str] = Field(default_factory=dict)
    vision_summaries: dict[str, Any] = Field(default_factory=dict)
    knowledge_version: str | None = None
    validated_concepts: list[str] = Field(default_factory=list)
    feature_summaries: dict[str, Any] = Field(default_factory=dict)
    evidence_by_tf: dict[str, Any] = Field(default_factory=dict)
    reasoning: dict[str, Any] = Field(default_factory=dict)
    risk: dict[str, Any] = Field(default_factory=dict)
    memory: dict[str, Any] = Field(default_factory=dict)
    learning: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, Any] = Field(default_factory=dict)
    provisional_bias: TradeBias = "NO TRADE"
    provisional_confidence: float = 0.0
    provisional_entry: str = "—"
    provisional_stop: str = "—"
    provisional_take: str = "—"
    provisional_rr: str = "—"
    provisional_grade: TradeGrade = "F"
    provisional_explanation: str = ""
    # Phase 11 — optional market verification payload (never required)
    market_verification: dict[str, Any] | None = None


class BrainRecommendation(BaseModel):
    pair: str
    timeframes: dict[str, str]
    summary: str
    recommendation: TradeBias
    entry: str = "—"
    stop_loss: str = "—"
    take_profit: str = "—"
    risk_reward: str = "—"
    confidence: float = Field(ge=0, le=100, default=0.0)
    trade_grade: TradeGrade = "F"
    supporting_evidence: list[str] = Field(default_factory=list)
    conflicting_evidence: list[str] = Field(default_factory=list)
    historical_support: HistoricalSupport = Field(default_factory=HistoricalSupport)
    warnings: list[str] = Field(default_factory=list)
    explanation: str = ""
    completeness: CompletenessReport | None = None
    conflicts: ConflictReport | None = None
    self_check: BrainSelfCheck | None = None
    reason_trace: ReasonTrace | None = None
    request_better_screenshot: bool = False
    # Phase 11 — optional market-data verification
    verification: VerificationSummary | None = None
