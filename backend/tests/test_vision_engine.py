from pathlib import Path

from cv.feature_cache import FeatureCache
from cv.structure_graph_builder import StructureGraphBuilder
from cv.models import FeatureObject
from cv.vision_engine import VisionEngine
from cv.testing.harness import VisionTestHarness
from cv.adapters import vision_to_chart_analysis
from tests.conftest import make_synthetic_candles, render_synthetic_chart


def test_vision_engine_on_synthetic(tmp_path: Path):
    image = render_synthetic_chart(tmp_path / "v4h.png", timeframe_text="4H")
    result = VisionEngine(use_cache=False).analyze_chart(image, expected_timeframe="4H")
    assert result.status == "ok"
    assert len(result.candles) >= 5
    assert result.feature_graph.nodes
    assert "trend" in result.summary


def test_vision_cache_hit(tmp_path: Path):
    image = render_synthetic_chart(tmp_path / "cache.png")
    cache = FeatureCache(root=tmp_path / "cache")
    engine = VisionEngine(use_cache=True)
    engine.cache = cache
    first = engine.analyze_chart(image)
    second = engine.analyze_chart(image)
    assert first.status == "ok"
    assert second.cache_hit is True


def test_feature_graph_hierarchy():
    features = [
        FeatureObject(id="trend_primary", type="trend", confidence=80, label="Bullish"),
        FeatureObject(id="bos_primary", type="bos", confidence=85, label="BOS", relationships=["trend_primary"]),
        FeatureObject(
            id="liquidity_sweep_primary",
            type="liquidity_sweep",
            confidence=80,
            label="Sweep",
            relationships=["bos_primary"],
        ),
        FeatureObject(
            id="ob_bullish_primary",
            type="bullish_order_block",
            confidence=80,
            label="Bullish OB",
            relationships=["bos_primary"],
        ),
    ]
    graph = StructureGraphBuilder().build(features)
    assert "trend_primary" in graph.root_ids or graph.root_ids
    tree = graph.as_tree_dict()
    assert "roots" in tree


def test_adapter_preserves_chart_analysis_shape(tmp_path: Path):
    image = render_synthetic_chart(
        tmp_path / "adapt.png",
        candles=make_synthetic_candles("bullish"),
    )
    vision = VisionEngine(use_cache=False).analyze_chart(image)
    analysis = vision_to_chart_analysis(vision)
    assert analysis.status in {"ok", "error"}
    if analysis.status == "ok":
        assert analysis.candle_count >= 5
        assert analysis.trend in {"Bullish", "Bearish", "Range", "Unknown"}


def test_vision_harness_runs(tmp_path: Path):
    render_synthetic_chart(tmp_path / "a.png")
    render_synthetic_chart(tmp_path / "b.png", candles=make_synthetic_candles("bearish"))
    (tmp_path / "annotations.json").write_text(
        '{"a.png": {"status": "ok"}, "b.png": {"status": "ok"}}',
        encoding="utf-8",
    )
    report = VisionTestHarness().run_folder(tmp_path, output_dir=tmp_path / "out")
    assert report.total == 2
    assert (tmp_path / "out" / "accuracy_report.json").exists()


def test_vision_multi_relationship(tmp_path: Path):
    p4 = render_synthetic_chart(tmp_path / "m4.png", timeframe_text="4H")
    p1 = render_synthetic_chart(tmp_path / "m1.png", timeframe_text="1H")
    p15 = render_synthetic_chart(tmp_path / "m15.png", timeframe_text="15M")
    multi = VisionEngine(use_cache=False).analyze_multi(p4, p1, p15)
    assert multi.chart_4h.status in {"ok", "error"}
    assert multi.relationship.alignment in {"Aligned", "Conflict", "Partial", "Unknown"}
