"""Vision Engine — full chart visual understanding pipeline (no trade recommendations)."""

from __future__ import annotations

from pathlib import Path

from cv.candle_extractor import CandleExtractor
from cv.chart_extractor import ChartExtractor
from cv.feature_cache import FeatureCache
from cv.fvg_detector import FVGDetector
from cv.image_validator import ImageValidator
from cv.liquidity_detector import LiquidityDetector
from cv.market_structure_detector import MarketStructureDetector
from cv.models import VisionChartResult, VisionMultiResult
from cv.mtf_relationship import MTFRelationshipAnalyzer
from cv.order_block_detector import OrderBlockDetector
from cv.structure_graph_builder import StructureGraphBuilder


class VisionEngine:
    def __init__(self, use_cache: bool = True) -> None:
        self.validator = ImageValidator()
        self.chart_extractor = ChartExtractor()
        self.candle_extractor = CandleExtractor()
        self.structure_detector = MarketStructureDetector()
        self.liquidity_detector = LiquidityDetector()
        self.order_block_detector = OrderBlockDetector()
        self.fvg_detector = FVGDetector()
        self.graph_builder = StructureGraphBuilder()
        self.mtf = MTFRelationshipAnalyzer()
        self.cache = FeatureCache() if use_cache else None

    def analyze_chart(
        self,
        image_path: str | Path,
        *,
        expected_timeframe: str | None = None,
        pair: str | None = None,
        use_cache: bool | None = None,
    ) -> VisionChartResult:
        path = str(image_path)
        caching = self.cache if (self.cache if use_cache is None else use_cache) else None
        if caching:
            cached = caching.get(path, expected_timeframe, pair=pair)
            if cached is not None:
                return cached

        validation = self.validator.validate(path)
        if not validation.ok or validation.enhanced is None or validation.original is None:
            result = VisionChartResult(
                status="error",
                error=validation.message or "Image Quality Too Low",
                image_path=path,
                quality_score=validation.quality_score,
                notes=[validation.message or "Image Quality Too Low"],
            )
            return result

        extraction = self.chart_extractor.extract(
            validation.original,
            validation.enhanced,
            validation.gray if validation.gray is not None else validation.enhanced[:, :, 0],
            expected_timeframe=expected_timeframe,
            pair=pair,
        )
        candles = self.candle_extractor.extract(extraction.chart_bgr)
        if len(candles) < 5:
            result = VisionChartResult(
                status="error",
                error="Image Quality Too Low",
                image_path=path,
                quality_score=validation.quality_score,
                meta=extraction.meta,
                candles=candles,
                notes=["Candles are not sufficiently visible."],
            )
            return result

        legacy = self.candle_extractor.to_legacy_candles(candles)
        features = []
        features.extend(self.structure_detector.detect(legacy, candles))
        features.extend(self.liquidity_detector.detect(legacy))
        features.extend(self.order_block_detector.detect(legacy))
        features.extend(self.fvg_detector.detect(legacy))

        graph = self.graph_builder.build(features)
        summary = self._summary(features, candles, extraction.meta.pair, extraction.meta.timeframe)

        result = VisionChartResult(
            status="ok",
            image_path=path,
            quality_score=validation.quality_score,
            meta=extraction.meta,
            candles=candles,
            features=features,
            feature_graph=graph,
            summary=summary,
            notes=self._notes(extraction.meta, features),
            cache_hit=False,
        )
        if caching:
            caching.put(path, result, expected_timeframe, pair=pair)
        return result

    def analyze_multi(
        self,
        chart_4h: str | Path,
        chart_1h: str | Path,
        chart_15m: str | Path,
        *,
        pair: str | None = None,
        timeframe_htf: str = "4H",
        timeframe_mtf: str = "1H",
        timeframe_ltf: str = "15M",
    ) -> VisionMultiResult:
        r4 = self.analyze_chart(
            chart_4h, expected_timeframe=timeframe_htf, pair=pair
        )
        r1 = self.analyze_chart(
            chart_1h, expected_timeframe=timeframe_mtf, pair=pair
        )
        r15 = self.analyze_chart(
            chart_15m, expected_timeframe=timeframe_ltf, pair=pair
        )
        relationship = self.mtf.compare(r4, r1, r15)

        statuses = [r4.status, r1.status, r15.status]
        if all(s == "ok" for s in statuses):
            status = "ok"
        elif all(s == "error" for s in statuses):
            status = "error"
        else:
            status = "partial"

        return VisionMultiResult(
            status=status,
            chart_4h=r4,
            chart_1h=r1,
            chart_15m=r15,
            relationship=relationship,
            notes=[
                "Phase 5 vision output only — no trade recommendation generated.",
                *relationship.notes,
            ],
        )

    def _summary(self, features, candles, pair, timeframe) -> dict:
        def first(ftype: str):
            for f in features:
                if f.type == ftype and f.confidence > 0:
                    return f.label or ftype
            return "Unknown"

        trend = "Unknown"
        for f in features:
            if f.id == "trend_primary":
                trend = str(f.location.get("trend") or f.label or "Unknown")
                break

        return {
            "pair": pair,
            "timeframe": timeframe,
            "candle_count": len(candles),
            "trend": trend,
            "bos": first("bos") != "Unknown",
            "choch": first("choch") != "Unknown",
            "liquidity_sweep": first("liquidity_sweep") != "Unknown",
            "bullish_order_block": any(f.type == "bullish_order_block" for f in features),
            "bearish_order_block": any(f.type == "bearish_order_block" for f in features),
            "bullish_fvg": any(f.type == "bullish_fvg" for f in features),
            "bearish_fvg": any(f.type == "bearish_fvg" for f in features),
            "feature_count": len([f for f in features if f.type != "unknown"]),
        }

    def _notes(self, meta, features) -> list[str]:
        notes = []
        if meta.pair == "Unknown":
            notes.append("Pair could not be detected confidently.")
        if meta.timeframe == "Unknown":
            notes.append("Timeframe could not be detected confidently.")
        unknowns = [f for f in features if f.type == "unknown"]
        if unknowns:
            notes.append(f"{len(unknowns)} feature(s) marked Unknown — never invented.")
        return notes
