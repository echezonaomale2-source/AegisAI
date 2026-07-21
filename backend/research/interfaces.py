"""Research platform interfaces — independently replaceable."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from cognitive.models.decision import CognitiveDecision
from cognitive.models.reasoning import ReasoningReport
from models.decision_schemas import TradeDecision
from research.models import (
    CalibrationState,
    PatternRecord,
    ResearchDashboard,
    ReviewReport,
    SelfCheckResult,
)


@runtime_checkable
class SelfCheckEngineProtocol(Protocol):
    def check(
        self,
        decision: TradeDecision | CognitiveDecision,
        *,
        reasoning: ReasoningReport | None = None,
    ) -> SelfCheckResult:
        ...


@runtime_checkable
class PostTradeReviewProtocol(Protocol):
    def review(
        self,
        trade_id: str,
        *,
        outcome: str,
        decision: TradeDecision,
        outcome_chart: Path | None = None,
        cognitive_archive: dict[str, Any] | None = None,
    ) -> ReviewReport:
        ...


@runtime_checkable
class ConfidenceCalibrationProtocol(Protocol):
    def record(self, predicted_confidence: float, *, success: bool) -> CalibrationState:
        ...

    def adjust(self, predicted_confidence: float) -> float:
        ...

    def state(self) -> CalibrationState:
        ...


@runtime_checkable
class PatternLibraryProtocol(Protocol):
    def record_outcome(
        self,
        features: list[str],
        *,
        outcome: str | None,
        confidence: float,
        risk_reward: float | None = None,
        holding_hours: float | None = None,
        was_no_trade: bool = False,
    ) -> PatternRecord:
        ...

    def most_reliable(self) -> PatternRecord | None:
        ...

    def least_reliable(self) -> PatternRecord | None:
        ...


@runtime_checkable
class LessonEngineProtocol(Protocol):
    def from_review(self, report: ReviewReport) -> list[str]:
        ...


@runtime_checkable
class ResearchDashboardProtocol(Protocol):
    def build(self) -> ResearchDashboard:
        ...
