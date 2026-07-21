"""Confidence engine interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.models.analysis import TradeAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision


@runtime_checkable
class ConfidenceEngineProtocol(Protocol):
    def score(
        self,
        analysis: TradeAnalysis,
        decision: TradeDecision,
        *,
        image_quality: dict[str, float] | None = None,
        historical_match: float | None = None,
    ) -> ConfidenceScorecard:
        """
        Final confidence from image quality, features, alignment,
        historical patterns, and structure/OB/liquidity strength.
        """
        ...
