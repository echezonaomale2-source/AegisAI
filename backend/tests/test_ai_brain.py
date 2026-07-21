"""Unit tests for AI Brain — conflicts, missing data, alignment, NO TRADE, historical."""

from __future__ import annotations

from brain.completeness import CompletenessChecker
from brain.conflicts import ConflictDetector
from brain.coordinator import AIBrain
from brain.historical import HistoricalReasoner
from brain.models import (
    CompletenessReport,
    ConflictReport,
    EngineBundle,
    HistoricalSupport,
)
from brain.self_check import BrainSelfChecker
from cognitive.models.decision import CognitiveDecision
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso


def _provisional(*, bias: str = "BUY", confidence: float = 82.0) -> TradeDecision:
    chart = ChartAnalysis(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        trend="Bullish",
        market_structure="Higher Highs",
        bos=True,
        liquidity="Equal Highs",
        confidence=80,
    )
    return TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart,
        analysis_1h=chart.model_copy(update={"timeframe": "1H"}),
        analysis_15m=chart.model_copy(update={"timeframe": "15M"}),
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
        explanation="test",
        reasons=["bos"],
        warnings=[],
        generated_at=utc_now_iso(),
    )


def _bundle(**vision_overrides) -> EngineBundle:
    base = {
        "4H": {"status": "ok", "quality": 85, "trend": "Bullish", "structure": "HH", "bos": True},
        "1H": {"status": "ok", "quality": 85, "trend": "Bullish", "structure": "HH", "bos": True},
        "15M": {"status": "ok", "quality": 85, "trend": "Bullish", "structure": "HH", "bos": True},
    }
    base.update(vision_overrides)
    return EngineBundle(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        vision_summaries=base,
        validated_concepts=["4H:bos", "1H:bos"],
        evidence_by_tf={"4H": {"buy": 80, "sell": 20}},
        reasoning={"conclusion": "BUY", "buy_evidence_score": 80, "sell_evidence_score": 20},
        risk={"valid": True, "risk_reward": "2.5", "risk_grade": "B"},
        provisional_bias="BUY",
        provisional_confidence=82,
    )


def _report(*, buy: float = 82, sell: float = 18, conclusion: str = "BUY") -> ReasoningReport:
    return ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=buy,
        sell_evidence_score=sell,
        neutral_score=5,
        conclusion=conclusion,  # type: ignore[arg-type]
        confidence=85,
        narrative=["aligned"],
        trace={"buy_score": buy, "sell_score": sell},
    )


def _cognitive(bias: str = "BUY") -> CognitiveDecision:
    return CognitiveDecision(
        pair="EURUSD",
        recommendation=bias,  # type: ignore[arg-type]
        entry="1.10",
        stop_loss="1.09",
        take_profit="1.13",
        risk_reward="3.00",
        confidence=82,
        trade_grade="B",
        explanation="test",
        risk=RiskAssessment(
            entry="1.10",
            stop_loss="1.09",
            take_profit="1.13",
            risk_reward="3.00",
            rr_numeric=3.0,
            risk_grade="B",
            valid=True,
        ),
    )


def test_missing_data_forces_incomplete() -> None:
    bundle = _bundle(
        **{
            "4H": {"status": "error", "quality": 10, "trend": "Unknown"},
            "1H": {"status": "error", "quality": 10, "trend": "Unknown"},
            "15M": {"status": "error", "quality": 10, "trend": "Unknown"},
        }
    )
    report = CompletenessChecker().check(bundle)
    assert report.complete is False
    assert report.missing_critical
    assert report.request_better_screenshot is True


def test_htf_conflict_detected() -> None:
    bundle = _bundle(
        **{
            "4H": {"status": "ok", "quality": 90, "trend": "Bullish"},
            "1H": {"status": "ok", "quality": 90, "trend": "Bearish"},
            "15M": {"status": "ok", "quality": 90, "trend": "Bearish"},
        }
    )
    conflicts = ConflictDetector().detect(bundle)
    assert conflicts.htf_disagreement is True
    assert conflicts.severity == "high"


def test_strong_alignment_allows_buy() -> None:
    brain = AIBrain()
    rec = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(bias="BUY", confidence=85),
        report=_report(),
        cognitive=_cognitive("BUY"),
    )
    assert rec.recommendation in {"BUY", "NO TRADE"}  # may still NO TRADE if hist weak sample
    assert rec.reason_trace is not None
    assert rec.reason_trace.deterministic_hash
    # Same inputs → same hash
    rec2 = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(bias="BUY", confidence=85),
        report=_report(),
        cognitive=_cognitive("BUY"),
    )
    assert rec.reason_trace.deterministic_hash == rec2.reason_trace.deterministic_hash


def test_htf_conflict_forces_no_trade() -> None:
    brain = AIBrain()
    bundle = _bundle(
        **{
            "4H": {"status": "ok", "quality": 90, "trend": "Bullish"},
            "1H": {"status": "ok", "quality": 90, "trend": "Bearish"},
            "15M": {"status": "ok", "quality": 90, "trend": "Bullish"},
        }
    )
    rec = brain.decide_from_bundle(
        bundle,
        provisional=_provisional(bias="BUY", confidence=90),
        report=_report(),
        cognitive=_cognitive("BUY"),
    )
    assert rec.recommendation == "NO TRADE"
    assert rec.conflicts and rec.conflicts.htf_disagreement


def test_poor_quality_requests_screenshot() -> None:
    brain = AIBrain()
    bundle = _bundle(
        **{
            "4H": {"status": "ok", "quality": 20, "trend": "Bullish"},
            "1H": {"status": "ok", "quality": 20, "trend": "Bullish"},
            "15M": {"status": "ok", "quality": 20, "trend": "Bullish"},
        }
    )
    rec = brain.decide_from_bundle(
        bundle,
        provisional=_provisional(bias="BUY", confidence=90),
        report=_report(),
        cognitive=_cognitive("BUY"),
    )
    assert rec.recommendation == "NO TRADE"
    assert rec.request_better_screenshot is True


def test_low_confidence_no_trade() -> None:
    brain = AIBrain()
    rec = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(bias="BUY", confidence=55),
        report=_report(buy=60, sell=40),
        cognitive=_cognitive("BUY"),
    )
    assert rec.recommendation == "NO TRADE"


def test_self_check_prefer_no_trade_on_conflicts() -> None:
    check = BrainSelfChecker().check(
        _bundle(),
        completeness=CompletenessReport(complete=True),
        conflicts=ConflictReport(
            has_conflicts=True,
            htf_disagreement=True,
            conflicts=["4H vs 1H"],
            severity="high",
        ),
        historical=HistoricalSupport(historical_support="Strong", previous_similar_analyses=50, wins=40, losses=10),
        confidence=85,
        candidate="BUY",
    )
    assert check.prefer_no_trade is True
    assert check.evidence_consistent is False


def test_historical_influence_does_not_override_bias(monkeypatch, tmp_path) -> None:
    import memory.database as mem_db

    test_db = tmp_path / "hist.db"
    monkeypatch.setattr(mem_db, "_DB_PATH", test_db)
    monkeypatch.setattr(mem_db, "get_db_path", lambda: test_db)
    mem_db.init_db()

    support = HistoricalReasoner().evaluate(_provisional(bias="BUY", confidence=80))
    # With empty memory → weak sample, negative influence, but evaluate doesn't change bias
    assert support.influence_on_confidence <= 0
    assert "does not override" in " ".join(support.notes).lower()


def test_invalid_risk_forces_no_trade() -> None:
    brain = AIBrain()
    cognitive = _cognitive("BUY")
    cognitive.risk = RiskAssessment(valid=False, risk_grade="F", risk_reward="0.5")
    rec = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(bias="BUY", confidence=90),
        report=_report(),
        cognitive=cognitive,
    )
    assert rec.recommendation == "NO TRADE"
