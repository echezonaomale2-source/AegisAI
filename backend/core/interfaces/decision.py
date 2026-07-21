"""Decision engine interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.models.analysis import TradeAnalysis
from models.decision_schemas import TradeDecision


@runtime_checkable
class DecisionEngineProtocol(Protocol):
    def decide(self, analysis: TradeAnalysis, *, pair_hint: str | None = None) -> TradeDecision:
        """Combine multi-TF SMC analysis into BUY / SELL / NO TRADE."""
        ...
