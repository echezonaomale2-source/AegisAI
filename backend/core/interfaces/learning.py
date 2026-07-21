"""Learning engine interface — incremental, never overwrites history."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LearningEngineProtocol(Protocol):
    def learn_from_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart: Path | None = None,
        notes: str | None = None,
    ) -> dict:
        """Compare prediction vs reality; update weights/patterns incrementally."""
        ...
