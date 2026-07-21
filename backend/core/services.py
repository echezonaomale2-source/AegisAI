"""
Service layer — clean, independently testable APIs for each AI module.

Implementations are injected via protocols so models can be swapped later
(e.g. GPU vision) without rewriting downstream code.
"""

from __future__ import annotations

from pathlib import Path

from core.adapters import LegacyConfidenceAdapter, LegacyDecisionAdapter, chart_model_to_chart_analysis
from core.cache import IntermediateCache
from core.engines.feature_extractor import FeatureExtractor
from core.engines.smc_engine import SmartMoneyEngine
from core.interfaces.chart import ExtractedChart
from core.interfaces.image import ImageQualityReport
from core.logging_setup import get_logger
from core.models.analysis import SMCAnalysis, TradeAnalysis
from core.models.chart import ChartModel
from core.models.features import FeatureSet
from core.models.memory import TradeMemory
from core.reconstruction import ChartReconstructor
from cv.image_validator import ImageValidator
from cv.models import VisionChartResult, VisionMultiResult
from cv.mtf_relationship import MTFRelationshipAnalyzer
from cv.vision_engine import VisionEngine
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision

log = get_logger("services")


class ImageService:
    """MODULE 1 — Image Validator."""

    def __init__(self, validator: ImageValidator | None = None) -> None:
        self._validator = validator or ImageValidator()

    def validate(self, path: str | Path) -> ImageQualityReport:
        path = Path(path)
        suffix = path.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
            return ImageQualityReport(
                ok=False,
                quality_score=0.0,
                message="Unsupported image format",
                path=str(path),
                unsupported_format=True,
            )
        result = self._validator.validate(str(path))
        return ImageQualityReport(
            ok=result.ok,
            quality_score=result.quality_score,
            sharpness=result.sharpness,
            message=result.message,
            path=str(path),
        )


class ChartService:
    """MODULE 2 — Chart Extractor (metadata + ROI via VisionEngine path)."""

    def __init__(self, vision: VisionEngine | None = None) -> None:
        self._vision = vision or VisionEngine(use_cache=True)

    def extract(self, path: str | Path, *, expected_timeframe: str | None = None) -> ExtractedChart:
        # Extraction is performed inside reconstruction; expose metadata-only result.
        result = self._vision.analyze_chart(path, expected_timeframe=expected_timeframe)
        ok = result.status == "ok"
        return ExtractedChart(
            ok=ok,
            pair=result.meta.pair,
            timeframe=result.meta.timeframe,
            detected_timeframe_label=result.meta.detected_timeframe_label,
            price_scale=result.meta.price_scale,
            chart_bounds=result.meta.chart_bounds,
            session_labels=list(result.meta.session_labels),
            pair_confidence=result.meta.pair_confidence,
            timeframe_confidence=result.meta.timeframe_confidence,
            source_path=str(path),
            notes=list(result.notes),
            clean_chart_ref=str(path) if ok else None,
        )


class VisionService:
    """MODULES 2–3 — Chart extraction + reconstruction → ChartModel only."""

    def __init__(
        self,
        reconstructor: ChartReconstructor | None = None,
        cache: IntermediateCache | None = None,
    ) -> None:
        self._reconstructor = reconstructor or ChartReconstructor()
        self._cache = cache

    def reconstruct(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> ChartModel:
        salt = expected_timeframe or ""
        if self._cache:
            cached = self._cache.get(path, "chart_model", ChartModel, salt=salt)
            if cached is not None:
                cached.cache_hit = True
                return cached

        model = self._reconstructor.reconstruct(path, expected_timeframe=expected_timeframe)
        if self._cache and model.status == "ok":
            self._cache.put(path, "chart_model", model, salt=salt)
        return model

    def analyze_vision_raw(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
    ) -> VisionChartResult:
        """Escape hatch for Phase 5 API — still available, not used by decision path."""
        return self._reconstructor._vision.analyze_chart(  # noqa: SLF001
            path, expected_timeframe=expected_timeframe
        )


class FeatureService:
    """MODULE 4 — Feature Extraction from ChartModel."""

    def __init__(self, extractor: FeatureExtractor | None = None, cache: IntermediateCache | None = None) -> None:
        self._extractor = extractor or FeatureExtractor()
        self._cache = cache

    def extract(self, chart: ChartModel) -> FeatureSet:
        if self._cache and chart.source_image_path:
            cached = self._cache.get(
                chart.source_image_path,
                "features",
                FeatureSet,
                salt=chart.timeframe,
            )
            if cached is not None:
                return cached
        features = self._extractor.extract(chart)
        if self._cache and chart.source_image_path and chart.status == "ok":
            self._cache.put(chart.source_image_path, "features", features, salt=chart.timeframe)
        return features


class SMCService:
    """MODULE 5 — Smart Money Engine (no BUY/SELL)."""

    def __init__(self, engine: SmartMoneyEngine | None = None) -> None:
        self._engine = engine or SmartMoneyEngine()
        self._mtf = MTFRelationshipAnalyzer()

    def analyze(self, chart: ChartModel, features: FeatureSet) -> SMCAnalysis:
        return self._engine.analyze(chart, features)

    def analyze_multi(
        self,
        chart_4h: ChartModel,
        features_4h: FeatureSet,
        chart_1h: ChartModel,
        features_1h: FeatureSet,
        chart_15m: ChartModel,
        features_15m: FeatureSet,
        *,
        pair: str = "Unknown",
    ) -> TradeAnalysis:
        a4 = self.analyze(chart_4h, features_4h)
        a1 = self.analyze(chart_1h, features_1h)
        a15 = self.analyze(chart_15m, features_15m)

        # Reuse MTF analyzer via lightweight VisionChartResult-shaped summaries.
        from cv.models import ChartMeta, VisionChartResult

        def _stub(chart: ChartModel, smc: SMCAnalysis) -> VisionChartResult:
            return VisionChartResult(
                status="ok" if chart.is_usable else "error",
                error=chart.error,
                quality_score=chart.image_quality_score,
                meta=ChartMeta(pair=chart.pair, timeframe=chart.timeframe),
                summary={
                    "trend": smc.trend,
                    "bos": smc.bos,
                    "choch": smc.choch,
                    "liquidity_sweep": smc.liquidity_sweep,
                },
                notes=list(smc.notes),
            )

        rel = self._mtf.compare(_stub(chart_4h, a4), _stub(chart_1h, a1), _stub(chart_15m, a15))
        resolved_pair = pair
        if resolved_pair == "Unknown":
            for p in (chart_4h.pair, chart_1h.pair, chart_15m.pair):
                if p and p != "Unknown":
                    resolved_pair = p
                    break

        return TradeAnalysis(
            pair=resolved_pair,
            analysis_4h=a4,
            analysis_1h=a1,
            analysis_15m=a15,
            alignment=rel.alignment,
            continuation=rel.continuation,
            reversal=rel.reversal,
            nested_structures=list(rel.nested_structures),
            relationship_notes=list(rel.notes),
            relationship_confidence=rel.confidence,
        )


class DecisionService:
    """MODULE 6 — Decision Engine."""

    def __init__(self, adapter: LegacyDecisionAdapter | None = None) -> None:
        self._adapter = adapter or LegacyDecisionAdapter()

    def decide(self, analysis: TradeAnalysis, *, pair_hint: str | None = None) -> TradeDecision:
        return self._adapter.decide(analysis, pair_hint=pair_hint)


class ConfidenceService:
    """MODULE 7 — Confidence Engine."""

    def __init__(self, adapter: LegacyConfidenceAdapter | None = None) -> None:
        self._adapter = adapter or LegacyConfidenceAdapter()

    def score(
        self,
        analysis: TradeAnalysis,
        decision: TradeDecision,
        *,
        image_quality: dict[str, float] | None = None,
        historical_match: float | None = None,
    ) -> ConfidenceScorecard:
        return self._adapter.score(
            analysis,
            decision,
            image_quality=image_quality,
            historical_match=historical_match,
        )


class MemoryService:
    """MODULE 8 — Memory Engine facade."""

    def __init__(self) -> None:
        from memory.memory_service import MemoryService as LegacyMemory

        self._legacy = LegacyMemory()

    def remember(
        self,
        decision: TradeDecision,
        analysis: TradeAnalysis,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
    ) -> TradeMemory:
        self._legacy.remember_decision(
            decision,
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
        )

        analysis_dump = analysis.model_dump()
        for key in ("analysis_4h", "analysis_1h", "analysis_15m"):
            block = analysis_dump.get(key) or {}
            block.pop("chart", None)
            block.pop("feature_set", None)
            analysis_dump[key] = block

        return TradeMemory(
            trade_id=decision.trade_id or "",
            pair=decision.pair,
            timestamp=decision.generated_at,
            chart_4h_path=str(chart_4h),
            chart_1h_path=str(chart_1h),
            chart_15m_path=str(chart_15m),
            reconstructed_4h=(
                analysis.analysis_4h.chart.model_dump() if analysis.analysis_4h.chart else None
            ),
            reconstructed_1h=(
                analysis.analysis_1h.chart.model_dump() if analysis.analysis_1h.chart else None
            ),
            reconstructed_15m=(
                analysis.analysis_15m.chart.model_dump() if analysis.analysis_15m.chart else None
            ),
            analysis=analysis_dump,
            decision=decision.overall_bias,
            entry=decision.entry,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            confidence=decision.confidence,
            explanation=decision.explanation,
            status=decision.status,
        )

    def apply_to_decision(self, decision: TradeDecision) -> TradeDecision:
        return self._legacy.apply_memory_to_decision(decision)

    @property
    def legacy(self):
        return self._legacy


class LearningService:
    """MODULE 9 — Learning Engine facade (SSOT: ResearchOrchestrator)."""

    def __init__(self, research: object | None = None) -> None:
        from research.orchestrator import ResearchOrchestrator as RO

        self._research = research or RO()

    def learn_from_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart: Path | None = None,
        notes: str | None = None,
    ) -> dict:
        _ = notes
        return self._research.process_outcome(
            trade_id,
            outcome=outcome,
            outcome_chart_path=str(outcome_chart) if outcome_chart else None,
        )

    def summary(self) -> dict:
        return self._research.learning_summary()


class SimilarityService:
    def __init__(self) -> None:
        from memory.similarity_engine import SimilarityEngine

        self._engine = SimilarityEngine()

    def find_similar(
        self,
        fingerprint_bits: list[int],
        *,
        direction: str | None = None,
        pair: str | None = None,
    ):
        return self._engine.find_similar(
            fingerprint_bits, direction=direction, pair=pair
        )


# Convenience: ChartModel → legacy ChartAnalysis for APIs that still need it.
def to_legacy_chart_analysis(chart: ChartModel) -> ChartAnalysis:
    return chart_model_to_chart_analysis(chart)
