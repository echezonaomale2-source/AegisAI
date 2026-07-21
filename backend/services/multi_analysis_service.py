"""Multi-timeframe pipeline — independent ChartModel reconstructions per TF."""

from __future__ import annotations

from pathlib import Path

from models.chart_schemas import MultiChartAnalysis
from services.chart_analysis_service import ChartAnalysisService


class MultiChartAnalysisService:
    def __init__(self) -> None:
        self.single = ChartAnalysisService()

    def analyze(
        self,
        chart_4h: str | Path,
        chart_1h: str | Path,
        chart_15m: str | Path,
    ) -> MultiChartAnalysis:
        result_4h = self.single.analyze(chart_4h, expected_timeframe="4H")
        result_1h = self.single.analyze(chart_1h, expected_timeframe="1H")
        result_15m = self.single.analyze(chart_15m, expected_timeframe="15M")

        statuses = [result_4h.status, result_1h.status, result_15m.status]
        if all(s == "ok" for s in statuses):
            status = "ok"
        elif all(s == "error" for s in statuses):
            status = "error"
        else:
            status = "partial"

        return MultiChartAnalysis(
            status=status,
            chart_4h=result_4h,
            chart_1h=result_1h,
            chart_15m=result_15m,
            notes=[
                "Phase 5.5: each chart reconstructed independently into ChartModel.",
                "Decision Engine consumes reconstructed models top-down (never raw images).",
            ],
        )
