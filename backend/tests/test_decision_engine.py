"""Step 6 — Decision Engine unit tests."""

from __future__ import annotations

from cognitive.engines.decision_engine import CognitiveDecisionEngine
from cognitive.engines.risk_engine import CognitiveRiskEngine
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment


def test_no_trade_emits_all_required_fields() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=40,
        sell_evidence_score=38,
        neutral_score=22,
        conclusion="NO TRADE",
        confidence=55,
        narrative=["Thin margin."],
        explanation="Thin margin.",
        gates_failed=["min_margin"],
        trace={"confidence": 55},
    )
    risk = CognitiveRiskEngine().assess(report, {})
    decision = CognitiveDecisionEngine().decide(report, risk, pair="EURUSD")
    assert decision.recommendation == "NO TRADE"
    assert decision.entry == "—"
    assert decision.stop_loss == "—"
    assert decision.take_profit == "—"
    assert decision.risk_reward == "—"
    assert decision.trade_grade == "F"
    assert decision.confidence >= 0
    assert decision.explanation
    assert decision.warnings
    assert "min_margin" in decision.gates_applied
    assert decision.reproducible_hash


def test_incomplete_levels_force_no_trade() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=85,
        sell_evidence_score=20,
        neutral_score=5,
        conclusion="BUY",
        confidence=88,
        narrative=["Strong BUY evidence."],
        explanation="Strong BUY evidence.",
        gates_failed=[],
        trace={"confidence": 88, "buy_score": 85},
    )
    risk = RiskAssessment(
        entry="—",
        stop_loss="—",
        take_profit="—",
        risk_reward="—",
        risk_grade="B",
        valid=True,
        notes=["Placeholder levels"],
    )
    decision = CognitiveDecisionEngine().decide(report, risk, pair="EURUSD")
    assert decision.recommendation == "NO TRADE"
    assert "incomplete_levels" in decision.gates_applied
    assert decision.trade_grade == "F"


def test_valid_buy_includes_levels_grade_explanation() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=85,
        sell_evidence_score=20,
        neutral_score=5,
        conclusion="BUY",
        confidence=88,
        narrative=["Strong BUY evidence."],
        explanation="Strong BUY evidence.",
        supporting_structures=["4H:bos:Bullish BOS"],
        gates_failed=[],
        trace={"confidence": 88, "buy_score": 85},
    )
    risk = RiskAssessment(
        entry="1.1000",
        stop_loss="1.0950",
        take_profit="1.1150",
        risk_reward="3.00",
        rr_numeric=3.0,
        risk_grade="A",
        valid=True,
        notes=["Favorable RR"],
    )
    decision = CognitiveDecisionEngine().decide(report, risk, pair="EURUSD")
    assert decision.recommendation == "BUY"
    assert decision.entry == "1.1000"
    assert decision.stop_loss == "1.0950"
    assert decision.take_profit == "1.1150"
    assert decision.risk_reward == "3.00"
    assert decision.confidence >= 70
    assert decision.trade_grade in {"A+", "A", "B", "C"}
    assert "Entry 1.1000" in decision.explanation
    assert not decision.gates_applied


def test_decision_deterministic_hash() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=82,
        sell_evidence_score=24,
        conclusion="NO TRADE",
        confidence=60,
        narrative=["test"],
        gates_failed=["min_confidence"],
        trace={"confidence": 60},
    )
    risk = RiskAssessment(valid=False, risk_grade="F")
    engine = CognitiveDecisionEngine()
    a = engine.decide(report, risk, pair="EURUSD")
    b = engine.decide(report, risk, pair="EURUSD")
    assert a.reproducible_hash == b.reproducible_hash


def test_decision_api_from_reasoning() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.post(
        "/api/cognitive/decision/from-reasoning",
        json={
            "pair": "EURUSD",
            "reasoning": {
                "pair": "EURUSD",
                "buy_evidence_score": 30,
                "sell_evidence_score": 28,
                "neutral_score": 40,
                "conclusion": "NO TRADE",
                "confidence": 40,
                "narrative": ["Inconclusive"],
                "explanation": "Inconclusive",
                "gates_failed": ["inconclusive_mass"],
                "trace": {"confidence": 40},
            },
        },
    )
    assert resp.status_code == 200
    d = resp.json()["decision"]
    assert d["recommendation"] == "NO TRADE"
    assert d["trade_grade"] == "F"
    assert d["explanation"]
    assert d["gates_applied"]
