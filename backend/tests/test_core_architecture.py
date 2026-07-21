"""Unit tests for Phase 5.5 core architecture (models, reconstruction, services, DI)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from core.adapters import chart_model_to_chart_analysis
from core.cache import IntermediateCache
from core.container import ServiceContainer, reset_container
from core.engines.feature_extractor import FeatureExtractor
from core.engines.smc_engine import SmartMoneyEngine
from core.models.chart import Candle, ChartModel, Trend
from core.pipeline import CorePipeline
from core.services import ImageService, VisionService


def _write_chart(path: Path) -> Path:
    img = Image.new("RGB", (640, 400), (12, 14, 20))
    draw = ImageDraw.Draw(img)
    # Fake candles
    x = 40
    for i in range(24):
        bull = i % 3 != 0
        body_top = 180 - i * 2
        body_bot = body_top + 30
        color = (40, 180, 120) if bull else (200, 70, 70)
        draw.rectangle([x, body_top, x + 12, body_bot], fill=color)
        draw.line([x + 6, body_top - 15, x + 6, body_bot + 15], fill=color, width=2)
        x += 22
    img.save(path)
    return path


@pytest.fixture
def chart_png(tmp_path: Path) -> Path:
    return _write_chart(tmp_path / "chart.png")


def test_image_service_rejects_unsupported(tmp_path: Path) -> None:
    bad = tmp_path / "note.txt"
    bad.write_text("not an image")
    report = ImageService().validate(bad)
    assert report.ok is False
    assert report.unsupported_format is True


def test_chart_model_is_image_free() -> None:
    model = ChartModel(
        status="ok",
        candles=[
            Candle(
                index=i,
                open=10 + i,
                high=12 + i,
                low=9 + i,
                close=11 + i,
                bullish=True,
                body_size=1,
                upper_wick=1,
                lower_wick=1,
                relative_position=i / 10,
            )
            for i in range(8)
        ],
        trend=Trend(direction="Bullish", confidence=90),
        bos=True,
    )
    dumped = model.model_dump()
    assert "ndarray" not in str(type(dumped))
    assert model.is_usable is True
    assert "pixels" not in dumped


def test_feature_and_smc_from_chart_model() -> None:
    candles = [
        Candle(
            index=i,
            open=100 + i,
            high=105 + i,
            low=98 + i,
            close=103 + i,
            bullish=True,
            body_size=3,
            upper_wick=2,
            lower_wick=2,
            relative_position=i / 12,
            confidence=80,
        )
        for i in range(12)
    ]
    chart = ChartModel(
        status="ok",
        pair="EURUSD",
        timeframe="1H",
        candles=candles,
        trend=Trend(direction="Bullish", confidence=92, impulse_move=True),
        market_structure_label="Higher Highs",
        bos=True,
        reconstruction_confidence=85,
    )
    features = FeatureExtractor().extract(chart)
    assert features.features
    assert features.primary("trend") is not None or features.primary("bos") is not None
    smc = SmartMoneyEngine().analyze(chart, features)
    assert smc.trend == "Bullish"
    assert smc.bos is True
    assert "BUY" not in " ".join(smc.reasoning)
    assert "SELL" not in " ".join(smc.reasoning)


def test_chart_model_to_legacy_analysis() -> None:
    chart = ChartModel(
        status="ok",
        pair="XAUUSD",
        timeframe="4H",
        candles=[
            Candle(
                index=0,
                open=1,
                high=2,
                low=0.5,
                close=1.5,
                bullish=True,
                body_size=0.5,
                upper_wick=0.5,
                lower_wick=0.5,
            )
        ]
        * 6,
        trend=Trend(direction="Bearish", confidence=80),
        market_structure_label="Lower Lows",
        choch=True,
    )
    # Fix candle indices
    chart.candles = [
        c.model_copy(update={"index": i}) for i, c in enumerate(chart.candles)
    ]
    analysis = chart_model_to_chart_analysis(chart)
    assert analysis.status == "ok"
    assert analysis.trend == "Bearish"
    assert analysis.choch is True


def test_intermediate_cache_roundtrip(tmp_path: Path, chart_png: Path) -> None:
    cache = IntermediateCache(root=tmp_path / "cache", model_version="test-v1")
    model = ChartModel(status="ok", pair="TEST", timeframe="15M", candles=[
        Candle(
            index=0,
            open=1,
            high=2,
            low=0.5,
            close=1.5,
            bullish=True,
            body_size=0.5,
            upper_wick=0.5,
            lower_wick=0.5,
        )
    ] * 5)
    model.candles = [c.model_copy(update={"index": i}) for i, c in enumerate(model.candles)]
    cache.put(chart_png, "chart_model", model, salt="15M")
    loaded = cache.get(chart_png, "chart_model", ChartModel, salt="15M")
    assert loaded is not None
    assert loaded.pair == "TEST"


def test_container_wires_protocols() -> None:
    reset_container()
    c = ServiceContainer(use_cache=False)
    assert c.image is not None
    assert c.vision is not None
    assert c.features is not None
    assert c.smc is not None
    assert c.decision is not None
    assert c.confidence is not None
    assert c.memory is not None
    assert c.learning is not None
    assert c.similarity is not None


def test_pipeline_reconstructs_synthetic(chart_png: Path) -> None:
    pipeline = CorePipeline(ServiceContainer(use_cache=False))
    model = pipeline.reconstruct_chart(chart_png, expected_timeframe="15M")
    # Synthetic charts may pass or fail quality — either way must be typed ChartModel
    assert isinstance(model, ChartModel)
    assert model.source_image_path is not None
    # Downstream conversion must never require pixels
    _ = chart_model_to_chart_analysis(model)


def test_vision_service_cache(tmp_path: Path, chart_png: Path) -> None:
    cache = IntermediateCache(root=tmp_path / "c", model_version="t")
    # Seed cache with a ready model to avoid depending on CV quality gates
    seed = ChartModel(
        status="ok",
        pair="CACHED",
        timeframe="1H",
        image_quality_score=88,
        candles=[
            Candle(
                index=i,
                open=1,
                high=2,
                low=0.5,
                close=1.5,
                bullish=True,
                body_size=0.5,
                upper_wick=0.5,
                lower_wick=0.5,
            )
            for i in range(6)
        ],
        trend=Trend(direction="Range", confidence=50),
        source_image_path=str(chart_png),
    )
    cache.put(chart_png, "chart_model", seed, salt="1H")

    class _Boom:
        def reconstruct(self, *args, **kwargs):
            raise AssertionError("should not call reconstructor on cache hit")

    svc = VisionService(reconstructor=_Boom(), cache=cache)  # type: ignore[arg-type]
    hit = svc.reconstruct(chart_png, expected_timeframe="1H")
    assert hit.cache_hit is True
    assert hit.pair == "CACHED"
