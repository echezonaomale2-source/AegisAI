"""Engine interfaces — each engine is independently replaceable."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from cognitive.models.decision import CognitiveDecision
from cognitive.models.evidence import Evidence
from cognitive.models.features import FeatureCollection
from cognitive.models.market import MarketModel
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from core.models.chart import ChartModel


@runtime_checkable
class VisionEngineProtocol(Protocol):
    def process(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartModel:
        """Screenshot → ChartModel (validation, extraction, quality)."""
        ...


@runtime_checkable
class ChartReconstructionEngineProtocol(Protocol):
    def rebuild(self, chart: ChartModel) -> MarketModel:
        """ChartModel → MarketModel (structure tree, zones, OB, FVG)."""
        ...


@runtime_checkable
class FeatureExtractionEngineProtocol(Protocol):
    def extract(self, market: MarketModel) -> FeatureCollection:
        ...


@runtime_checkable
class EvidenceEngineProtocol(Protocol):
    def evaluate(
        self,
        features: FeatureCollection,
        *,
        image_quality: float = 100.0,
        feature_weights: dict[str, float] | None = None,
    ) -> Evidence:
        ...


@runtime_checkable
class ReasoningEngineProtocol(Protocol):
    def reason(
        self,
        evidence_by_tf: dict[str, Evidence],
        *,
        historical_bias: float = 0.0,
        pair: str = "Unknown",
    ) -> ReasoningReport:
        ...


@runtime_checkable
class CognitiveDecisionEngineProtocol(Protocol):
    def decide(
        self,
        report: ReasoningReport,
        risk: RiskAssessment,
        *,
        pair: str = "Unknown",
    ) -> CognitiveDecision:
        ...


@runtime_checkable
class CognitiveRiskEngineProtocol(Protocol):
    def assess(
        self,
        report: ReasoningReport,
        markets: dict[str, MarketModel],
    ) -> RiskAssessment:
        ...


@runtime_checkable
class CognitiveMemoryEngineProtocol(Protocol):
    def remember(self, decision: CognitiveDecision, **paths: Path) -> None:
        ...


@runtime_checkable
class CognitiveLearningEngineProtocol(Protocol):
    def learn_from_outcome(self, trade_id: str, *, outcome: str, **kwargs) -> dict:
        ...
