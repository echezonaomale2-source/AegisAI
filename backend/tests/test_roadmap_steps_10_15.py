"""Steps 10–15 completion tests."""

from __future__ import annotations

import json
from pathlib import Path

from core.analysis_jobs import ANALYSIS_SCHEMA_VERSION, AnalysisJobStore
from cv.feature_cache import FeatureCache
from cv.testing.harness import VisionTestHarness, _predict_fields
from dataset.toolkit import empty_annotation, import_images, validate_dataset
from evaluation.engine import EvaluationEngine
from research.confidence_calibration import ConfidenceCalibrationEngine


def test_calibration_exposes_ece() -> None:
    state = ConfidenceCalibrationEngine().state()
    assert hasattr(state, "expected_calibration_error")
    # May be None when no samples — still a defined field
    assert state.expected_calibration_error is None or state.expected_calibration_error >= 0


def test_evaluation_report_includes_quality_and_learning() -> None:
    report = EvaluationEngine().build_report(persist=False)
    assert report.trade_reviews is not None
    assert hasattr(report.trade_reviews, "decision_quality_distribution")
    assert hasattr(report.learning, "effectiveness_score")
    assert hasattr(report.calibration, "expected_calibration_error")


def test_evaluation_false_detection_counter() -> None:
    eng = EvaluationEngine()
    before = int(eng.counters.get("vision.false_verified") or 0)
    eng.record_false_detection(count=2)
    assert int(eng.counters.get("vision.false_verified") or 0) >= before + 2


def test_dataset_import_never_auto_labels(tmp_path: Path) -> None:
    img = tmp_path / "chart.png"
    img.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )
    result = import_images(img, version="test_v1", base=tmp_path / "cv_datasets")
    assert result["imported_new"] == 1
    ann = json.loads(
        (tmp_path / "cv_datasets" / "test_v1" / "annotations.json").read_text(encoding="utf-8")
    )
    entry = next(iter(ann.values()))
    assert entry["labeled"] is False
    assert entry["trend"] is None
    assert entry["bos"] is None
    stub = empty_annotation()
    assert stub["labeled"] is False


def test_dataset_validate_unlabeled_ok(tmp_path: Path) -> None:
    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    import_images(img, version="v_val", base=tmp_path / "ds")
    report = validate_dataset("v_val", base=tmp_path / "ds")
    assert report["ok"] is True
    assert report["unlabeled"] >= 1


def test_harness_predicts_fvg_supply_demand_fields() -> None:
    from cv.models import ChartMeta, VisionChartResult

    result = VisionChartResult(
        status="ok",
        meta=ChartMeta(pair="EURUSD", timeframe="1H"),
        candles=[],
        summary={
            "trend": "Bullish",
            "bos": True,
            "bullish_fvg": True,
            "supply_zone": True,
            "demand_zone": False,
        },
    )
    pred = _predict_fields(result)
    assert "bullish_fvg" in pred
    assert "supply" in pred
    assert "demand" in pred


def test_feature_cache_eviction(tmp_path: Path) -> None:
    cache = FeatureCache(root=tmp_path / "vc", max_files=3)
    for i in range(5):
        p = tmp_path / f"i{i}.png"
        p.write_bytes(b"x" * (10 + i))
        from cv.models import ChartMeta, VisionChartResult

        cache.put(
            str(p),
            VisionChartResult(status="ok", meta=ChartMeta(), candles=[], summary={}),
        )
    assert len(list((tmp_path / "vc").glob("*.json"))) <= 3


def test_analysis_job_lifecycle() -> None:
    store = AnalysisJobStore()
    job_id = store.create(
        pair="EURUSD",
        chart_4h="a.png",
        chart_1h="b.png",
        chart_15m="c.png",
    )
    store.mark_running(job_id)
    store.mark_done(job_id, trade_id="t1", payload={"ok": True})
    row = store.get(job_id)
    assert row is not None
    assert row["status"] == "done"
    assert ANALYSIS_SCHEMA_VERSION


def test_trade_store_schema_version(tmp_path: Path) -> None:
    from models.chart_schemas import ChartAnalysis
    from models.decision_schemas import ConfidenceScorecard, TradeDecision
    from models.schemas import utc_now_iso
    from storage.trade_store import TradeStore

    img = tmp_path / "c.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n")
    chart = ChartAnalysis(status="ok", pair="EURUSD", timeframe="1H", confidence=50)
    td = TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart,
        analysis_1h=chart,
        analysis_15m=chart,
        overall_bias="NO TRADE",
        entry="—",
        stop_loss="—",
        take_profit="—",
        risk_reward="—",
        target_liquidity="—",
        confidence=40,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=40,
            mtf_1h_alignment=40,
            ltf_15m_confirmation=40,
            liquidity=40,
            order_block=40,
            fair_value_gap=40,
            market_structure=40,
            overall=40,
            weights={},
        ),
        explanation="test",
        generated_at=utc_now_iso(),
    )
    store = TradeStore(root=tmp_path / "trades")
    saved = store.save(td, chart_4h=img, chart_1h=img, chart_15m=img)
    rec = store.get_trade(saved.trade_id or "")
    assert rec is not None
    assert rec.get("analysis_schema_version") == ANALYSIS_SCHEMA_VERSION


def test_e2e_modules_import_and_eval_list() -> None:
    """Smoke end-to-end wiring across cognitive + eval modules."""
    from cognitive.engines.evidence_engine import EvidenceEngine
    from cognitive.engines.reasoning_engine import ReasoningEngine
    from cognitive.engines.decision_engine import CognitiveDecisionEngine
    from cognitive.models.evidence import Evidence
    from cognitive.models.risk import RiskAssessment
    from knowledge.engine import KnowledgeEngine

    assert KnowledgeEngine().get_concept("bos") is not None
    weak = Evidence(buy_weight=1, sell_weight=1, neutral_weight=10, missing_evidence=["bos"])
    report = ReasoningEngine().reason({"4H": weak, "1H": weak, "15M": weak}, pair="EURUSD")
    assert report.conclusion == "NO TRADE"
    decision = CognitiveDecisionEngine().decide(
        report, RiskAssessment(valid=False, risk_grade="F"), pair="EURUSD"
    )
    assert decision.recommendation == "NO TRADE"
    reports = EvaluationEngine().list_reports(limit=3)
    assert isinstance(reports, list)


def test_dataset_and_jobs_api() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    assert client.get("/api/evaluation/reports").status_code == 200
    assert client.get("/api/learning/summary").status_code == 200
