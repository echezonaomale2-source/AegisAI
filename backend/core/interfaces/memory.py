"""Memory engine interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from core.models.analysis import TradeAnalysis
from core.models.memory import TradeMemory
from models.decision_schemas import TradeDecision


@runtime_checkable
class MemoryEngineProtocol(Protocol):
    def remember(
        self,
        decision: TradeDecision,
        analysis: TradeAnalysis,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
    ) -> TradeMemory:
        ...

    def apply_to_decision(self, decision: TradeDecision) -> TradeDecision:
        ...
