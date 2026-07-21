"""Chart extraction interface — produces a clean chart image reference."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ExtractedChart(BaseModel):
    """Clean chart extraction metadata (pixel buffers stay in implementation layer)."""

    ok: bool
    pair: str = "Unknown"
    timeframe: str = "Unknown"
    detected_timeframe_label: str | None = None
    price_scale: dict[str, Any] | None = None
    chart_bounds: dict[str, int] | None = None
    session_labels: list[str] = Field(default_factory=list)
    pair_confidence: float = 0.0
    timeframe_confidence: float = 0.0
    source_path: str | None = None
    notes: list[str] = Field(default_factory=list)
    # Opaque handle for implementation (e.g. path to temp cleaned image).
    clean_chart_ref: str | None = None


@runtime_checkable
class ChartExtractorProtocol(Protocol):
    def extract(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ExtractedChart:
        ...
