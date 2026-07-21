"""
Core AI pipeline — orchestrates the full Phase 5.5 flow.

Uploaded Screenshots
  → Image Validation
  → Chart Extraction / Reconstruction (ChartModel)
  → Feature Extraction
  → Smart Money Engine
  → Decision Engine
  → Confidence Engine
  → Trade Recommendation
  → Trade Memory
  → Learning Engine (on outcome)

Decision / SMC / Confidence never receive raw images — only ChartModel / TradeAnalysis.
"""

from __future__ import annotations

from pathlib import Path

from core.container import ServiceContainer, get_container
from core.logging_setup import get_logger
from core.models.analysis import TradeAnalysis
from core.models.chart import ChartModel
from core.services import to_legacy_chart_analysis
from models.chart_schemas import ChartAnalysis, MultiChartAnalysis
from models.decision_schemas import TradeDecision
from storage.trade_store import TradeStore

log = get_logger("pipeline")


class CorePipeline:
    def __init__(self, container: ServiceContainer | None = None) -> None:
        self.c = container or get_container()
        self.trade_store = TradeStore()

    def reconstruct_chart(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartModel:
        quality = self.c.image.validate(path)
        if not quality.ok:
            return ChartModel(
                status="error",
                error=quality.message or "Image Quality Too Low",
                image_quality_score=quality.quality_score,
                source_image_path=str(path),
                notes=[quality.message or "Image Quality Too Low"],
            )
        return self.c.vision.reconstruct(path, expected_timeframe=expected_timeframe)

    def analyze_chart_model(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> tuple[ChartModel, object, object]:
        chart = self.reconstruct_chart(path, expected_timeframe=expected_timeframe)
        features = self.c.features.extract(chart)
        smc = self.c.smc.analyze(chart, features)
        return chart, features, smc

    def build_trade_analysis(
        self,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        pair: str = "Unknown",
    ) -> TradeAnalysis:
        c4 = self.reconstruct_chart(chart_4h, expected_timeframe="4H")
        c1 = self.reconstruct_chart(chart_1h, expected_timeframe="1H")
        c15 = self.reconstruct_chart(chart_15m, expected_timeframe="15M")
        f4 = self.c.features.extract(c4)
        f1 = self.c.features.extract(c1)
        f15 = self.c.features.extract(c15)
        return self.c.smc.analyze_multi(c4, f4, c1, f1, c15, f15, pair=pair)

    def decide(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        persist: bool = True,
    ) -> TradeDecision:
        analysis = self.build_trade_analysis(
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            pair=pair,
        )
        decision = self.c.decision.decide(analysis, pair_hint=pair)

        image_quality = {
            "4H": analysis.analysis_4h.chart.image_quality_score if analysis.analysis_4h.chart else 0.0,
            "1H": analysis.analysis_1h.chart.image_quality_score if analysis.analysis_1h.chart else 0.0,
            "15M": analysis.analysis_15m.chart.image_quality_score if analysis.analysis_15m.chart else 0.0,
        }
        scorecard = self.c.confidence.score(analysis, decision, image_quality=image_quality)
        # Attach enriched scorecard; keep DecisionEngine confidence (already threshold-gated).
        decision = decision.model_copy(update={"confidence_scorecard": scorecard})

        decision = self.c.memory.apply_to_decision(decision)

        if persist:
            decision = self.trade_store.save(
                decision,
                chart_4h=chart_4h,
                chart_1h=chart_1h,
                chart_15m=chart_15m,
            )
            trade_dir = self.trade_store.root / (decision.trade_id or "")
            self.c.memory.remember(
                decision,
                analysis,
                chart_4h=trade_dir / next(trade_dir.glob("chart_4h.*")),
                chart_1h=trade_dir / next(trade_dir.glob("chart_1h.*")),
                chart_15m=trade_dir / next(trade_dir.glob("chart_15m.*")),
            )

        log.info(
            "pipeline decision pair=%s bias=%s conf=%.1f alignment=%s",
            decision.pair,
            decision.overall_bias,
            decision.confidence,
            analysis.alignment,
        )
        return decision

    def analyze_single_legacy(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartAnalysis:
        chart = self.reconstruct_chart(path, expected_timeframe=expected_timeframe)
        return to_legacy_chart_analysis(chart)

    def analyze_multi_legacy(
        self,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
    ) -> MultiChartAnalysis:
        return MultiChartAnalysis(
            chart_4h=self.analyze_single_legacy(chart_4h, expected_timeframe="4H"),
            chart_1h=self.analyze_single_legacy(chart_1h, expected_timeframe="1H"),
            chart_15m=self.analyze_single_legacy(chart_15m, expected_timeframe="15M"),
        )
