"""Single-chart analysis — Phase 5.5 ChartModel reconstruction → ChartAnalysis."""

from __future__ import annotations

from pathlib import Path

from core.adapters import chart_model_to_chart_analysis
from core.reconstruction import ChartReconstructor
from models.chart_schemas import ChartAnalysis


class ChartAnalysisService:
    """
    Analyze one chart screenshot independently.

    Uses ChartReconstructor directly (no ServiceContainer) so ReviewEngine /
    MemoryService can depend on this class without circular DI.
    """

    def __init__(self) -> None:
        self.reconstructor = ChartReconstructor()

    def analyze(
        self,
        image_path: str | Path,
        expected_timeframe: str | None = None,
        *,
        pair: str | None = None,
    ) -> ChartAnalysis:
        model = self.reconstructor.reconstruct(
            image_path,
            expected_timeframe=expected_timeframe,
            pair=pair,
        )
        return chart_model_to_chart_analysis(model)

    def analyze_vision(
        self,
        image_path: str | Path,
        expected_timeframe: str | None = None,
        *,
        pair: str | None = None,
    ):
        """Return full Phase 5 vision graph (no trade recommendation)."""
        return self.reconstructor._vision.analyze_chart(  # noqa: SLF001
            image_path,
            expected_timeframe=expected_timeframe,
            pair=pair,
        )
