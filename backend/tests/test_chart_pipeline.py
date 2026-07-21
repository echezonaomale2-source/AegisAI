from pathlib import Path

from services.chart_analysis_service import ChartAnalysisService
from services.multi_analysis_service import MultiChartAnalysisService
from tests.conftest import make_synthetic_candles, render_synthetic_chart
from vision.candle_detector import detect_candles
from vision.chart_roi import detect_chart_roi
from vision.preprocessing import preprocess_image


def test_preprocess_and_roi(tmp_path: Path):
    image_path = render_synthetic_chart(tmp_path / "chart.png")
    pre = preprocess_image(str(image_path))
    assert pre.quality_ok is True
    roi = detect_chart_roi(pre.enhanced, pre.gray)
    assert roi.width > 100
    assert roi.height > 100


def test_candle_detection_on_synthetic(tmp_path: Path):
    image_path = render_synthetic_chart(
        tmp_path / "candles.png",
        candles=make_synthetic_candles("bullish"),
    )
    pre = preprocess_image(str(image_path))
    roi = detect_chart_roi(pre.enhanced, pre.gray)
    candles = detect_candles(roi.image)
    assert len(candles) >= 5


def test_single_chart_analysis_service(tmp_path: Path):
    image_path = render_synthetic_chart(tmp_path / "single.png", timeframe_text="1H")
    result = ChartAnalysisService().analyze(image_path, expected_timeframe="1H")
    assert result.status == "ok"
    assert result.candle_count >= 5
    assert result.confidence > 0
    assert result.confidence_breakdown is not None


def test_multi_chart_independent(tmp_path: Path):
    p4 = render_synthetic_chart(tmp_path / "4h.png", timeframe_text="4H")
    p1 = render_synthetic_chart(
        tmp_path / "1h.png",
        candles=make_synthetic_candles("bearish"),
        timeframe_text="1H",
    )
    p15 = render_synthetic_chart(
        tmp_path / "15m.png",
        candles=make_synthetic_candles("range"),
        timeframe_text="15M",
    )
    multi = MultiChartAnalysisService().analyze(p4, p1, p15)
    assert multi.chart_4h.status == "ok"
    assert multi.chart_1h.status == "ok"
    assert multi.chart_15m.status == "ok"
    # Independence: results are separate objects.
    assert multi.chart_4h is not multi.chart_1h
