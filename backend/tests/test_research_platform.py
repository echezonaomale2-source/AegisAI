"""Unit tests for Phase 7 research: review, calibration, patterns, self-checks."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from research.confidence_calibration import ConfidenceCalibrationEngine
from research.decision_quality import DecisionQualityClassifier
from research.lesson_engine import LessonEngine
from research.models import ResearchScorecard, ReviewReport
from research.pattern_library import PatternLibrary
from research.post_trade_review import PostTradeReviewEngine
from research.self_checks import SelfCheckEngine
from cognitive.models.reasoning import ReasoningReport


def _decision(*, bias: str = "BUY", confidence: float = 82.0) -> TradeDecision:
    ok = ChartAnalysis(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        trend="Bullish",
        market_structure="Higher Highs",
        bos=True,
        liquidity="Equal Highs",
        liquidity_sweep=True,
        bullish_order_block=True,
        fair_value_gap=True,
        fvg_type="Bullish FVG",
        confidence=80,
    )
    m15 = ok.model_copy(
        update={"timeframe": "15M", "bos": True, "liquidity_sweep": True, "choch": False}
    )
    return TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=ok,
        analysis_1h=ok.model_copy(update={"timeframe": "1H"}),
        analysis_15m=m15,
        overall_bias=bias,  # type: ignore[arg-type]
        entry="1.10",
        stop_loss="1.09",
        take_profit="1.13",
        risk_reward="3.00",
        target_liquidity="Equal highs",
        confidence=confidence,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=80,
            mtf_1h_alignment=75,
            ltf_15m_confirmation=70,
            liquidity=70,
            order_block=70,
            fair_value_gap=70,
            market_structure=80,
            overall=confidence,
            weights={},
        ),
        explanation="Test decision",
        reasons=["test"],
        warnings=[],
        generated_at=utc_now_iso(),
        trade_id="test-trade-1",
    )


def test_decision_quality_independent_of_outcome() -> None:
    clf = DecisionQualityClassifier()
    excellent = ResearchScorecard(
        higher_timeframe_alignment=90,
        entry_quality=90,
        stop_loss_placement=90,
        take_profit_placement=90,
        market_structure_detection=90,
        liquidity_detection=90,
        order_block_quality=90,
        fvg_quality=90,
        confidence_calibration=90,
        overall_analysis_quality=90,
    )
    avoid = ResearchScorecard(overall_analysis_quality=30)
    assert clf.classify(excellent) == "Excellent"
    assert clf.classify(avoid) == "Avoid"


def test_post_trade_review_scorecard_and_questions(tmp_path) -> None:
    # Isolate research DB by relying on shared test DB — review is pure function mostly
    engine = PostTradeReviewEngine()
    report = engine.review(
        "t1",
        outcome="TAKE_PROFIT",
        decision=_decision(),
    )
    assert report.scorecard.overall_analysis_quality > 0
    assert "Was the higher-timeframe bias correct?" in report.questions
    assert report.decision_quality in {"Excellent", "Good", "Acceptable", "Borderline", "Avoid"}
    assert report.strengths or report.weaknesses


def test_calibration_does_not_move_on_single_trade(tmp_path, monkeypatch) -> None:
    import research.confidence_calibration as cal_mod
    import research.database as db_mod
    from pathlib import Path
    import memory.database as mem_db

    # Use temp DB
    test_db = tmp_path / "cal.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    db_mod.init_research_db()

    eng = ConfidenceCalibrationEngine()
    before = eng.state().adjustment_factor
    eng.record(95.0, success=False)  # one overconfident miss
    after = eng.state().adjustment_factor
    assert after == before  # need MIN_SAMPLES_FOR_ADJUSTMENT
    assert eng.state().sample_count == 1


def test_calibration_adjust_before_warmup_is_identity(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import research.database as db_mod

    test_db = tmp_path / "cal2.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    db_mod.init_research_db()

    eng = ConfidenceCalibrationEngine()
    assert eng.adjust(88.0) == 88.0


def test_pattern_library_incremental(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import research.database as db_mod

    test_db = tmp_path / "pat.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    db_mod.init_research_db()

    lib = PatternLibrary()
    feats = ["bos", "bullish_order_block", "liquidity_sweep"]
    a = lib.record_outcome(feats, outcome="TAKE_PROFIT", confidence=80, risk_reward=2.0)
    b = lib.record_outcome(feats, outcome="STOP_LOSS", confidence=75, risk_reward=1.8)
    assert b.occurrences == 2
    assert b.wins == 1 and b.losses == 1
    assert a.pattern_id == b.pattern_id
    c = lib.record_outcome(feats, outcome=None, confidence=60, was_no_trade=True)
    assert c.no_trade_recommendations == 1


def test_self_check_forces_no_trade_on_conflicts() -> None:
    decision = _decision(bias="BUY", confidence=75)
    reasoning = ReasoningReport(
        buy_evidence_score=50,
        sell_evidence_score=48,
        neutral_score=20,
        conclusion="BUY",
        confidence=72,
        missing=["liquidity", "order_block", "fvg", "swing_points", "trend"],
        conflicting=[],
        conflicts_summary=["c1", "c2", "c3"],
    )
    # Empty conflicting but many missing + thin margin
    result = SelfCheckEngine().check(decision, reasoning=reasoning)
    assert result.force_no_trade is True


def test_lesson_engine_produces_lessons() -> None:
    report = ReviewReport(
        trade_id="x",
        outcome="STOP_LOSS",
        htf_bias_correct=False,
        m15_confirmation_valid=False,
        confidence_appropriate=False,
        should_have_been_no_trade=True,
        decision_quality="Borderline",
    )
    lessons = LessonEngine().from_review(report)
    assert lessons
    assert any("NO TRADE" in x or "Confidence" in x or "higher-timeframe" in x for x in lessons)


def test_analysis_cache_roundtrip(tmp_path, monkeypatch) -> None:
    import memory.database as mem_db
    import research.database as db_mod
    from research.analysis_cache import AnalysisCache

    test_db = tmp_path / "cache.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()
    db_mod.init_research_db()

    img = tmp_path / "a.png"
    img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    cache = AnalysisCache()
    cache.put({"ok": True, "n": 1}, img, salt="test")
    hit = cache.get(img, salt="test")
    assert hit == {"ok": True, "n": 1}
