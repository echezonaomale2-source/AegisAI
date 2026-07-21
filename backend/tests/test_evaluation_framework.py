"""Automated tests for Evaluation Framework."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from evaluation.engine import EvaluationEngine
from evaluation.health import HealthReporter, _grade
from evaluation.models import EvaluationReport, VisionMetrics
from evaluation.quality_gates import ABTestService, QualityGateService
from evaluation.path_logger import DecisionPathLogger


def _decision(bias: str = "NO TRADE", confidence: float = 65.0) -> TradeDecision:
    chart = ChartAnalysis(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        trend="Bullish",
        market_structure="Higher Highs",
        bos=True,
        liquidity="Equal Highs",
        confidence=70,
    )
    return TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart,
        analysis_1h=chart.model_copy(update={"timeframe": "1H"}),
        analysis_15m=chart.model_copy(update={"timeframe": "15M", "bos": True}),
        overall_bias=bias,  # type: ignore[arg-type]
        entry="—",
        stop_loss="—",
        take_profit="—",
        risk_reward="—",
        target_liquidity="None",
        confidence=confidence,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=70,
            mtf_1h_alignment=70,
            ltf_15m_confirmation=70,
            liquidity=70,
            order_block=70,
            fair_value_gap=70,
            market_structure=70,
            overall=confidence,
            weights={"buy_evidence": 60, "sell_evidence": 20, "neutral": 20},
        ),
        explanation="eval test",
        reasons=["test"],
        warnings=["Knowledge version: 1.0"],
        generated_at=utc_now_iso(),
        trade_id="eval-trade-1",
    )


def test_health_grade_bands() -> None:
    assert _grade(90) == "Excellent"
    assert _grade(75) == "Good"
    assert _grade(60) == "Improving"
    assert _grade(45) == "Needs Review"
    assert _grade(10) == "Critical"


def test_record_decision_and_build_report(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import evaluation.database as eval_db
    import research.database as research_db

    test_db = tmp_path / "eval.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    research_db.init_research_db()
    eval_db.init_evaluation_db()

    eng = EvaluationEngine()
    log_id = eng.record_decision(
        _decision("BUY", 82),
        validated_concepts=["bos", "bullish_order_block"],
        evidence_summary={"buy_score": 70, "sell_score": 20, "neutral_score": 10},
    )
    assert log_id
    report = eng.build_report(persist=True)
    assert report.decisions.buy_recommendations >= 1
    assert report.decisions.total_decisions >= 1
    assert report.health.overall_grade in {
        "Excellent",
        "Good",
        "Improving",
        "Needs Review",
        "Critical",
        "Unknown",
    }
    assert eng.latest_report() is not None


def test_path_logger_outcome_attach(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import evaluation.database as eval_db

    test_db = tmp_path / "paths.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    eval_db.init_evaluation_db()

    logger = DecisionPathLogger()
    entry = logger.log(
        trade_id="t1",
        input_summary={"pair": "XAUUSD"},
        validated_concepts=["bos"],
        evidence_summary={},
        reasoning_summary={},
        decision="BUY",
        confidence=80,
    )
    assert entry.log_id
    n = logger.attach_outcome("t1", outcome="TAKE_PROFIT", review_scores={"overall": 80})
    assert n == 1
    recent = logger.recent(5)
    assert recent[0]["outcome"] == "TAKE_PROFIT"


def test_quality_gate_requires_improvement() -> None:
    gates = QualityGateService()
    reject = gates.evaluate(
        gate_name="test",
        baseline_score=80,
        candidate_score=80.5,
        min_improvement=2.0,
    )
    assert reject.accepted is False
    accept = gates.evaluate(
        gate_name="test",
        baseline_score=80,
        candidate_score=83,
        min_improvement=2.0,
    )
    assert accept.accepted is True


def test_ab_test_lifecycle(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import evaluation.database as eval_db

    test_db = tmp_path / "ab.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    eval_db.init_evaluation_db()

    svc = ABTestService()
    started = svc.start("bos-v2", candidate_variant="bos_v2")
    assert started.status == "running"
    done = svc.complete(
        started.test_id,
        baseline_score=70,
        candidate_score=75,
        min_improvement=2.0,
    )
    assert done.status == "accepted"
    assert done.gate_result and done.gate_result.accepted


def test_vision_health_unknown_without_samples() -> None:
    reporter = HealthReporter()
    report = EvaluationReport(
        report_id="x",
        created_at=utc_now_iso(),
        vision=VisionMetrics(),
    )
    health = reporter.build(report)
    vision = next(m for m in health.modules if m.module == "Vision Engine")
    assert vision.grade == "Unknown"
