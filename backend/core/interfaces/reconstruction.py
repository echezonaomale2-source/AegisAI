"""Chart reconstruction interface — heart of the architecture."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from core.models.chart import ChartModel


@runtime_checkable
class ChartReconstructorProtocol(Protocol):
    def reconstruct(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartModel:
        """
        Build an internal ChartModel from a screenshot.

        Output must contain no pixel buffers. Unknown fields stay Unknown.
        """
        ...
