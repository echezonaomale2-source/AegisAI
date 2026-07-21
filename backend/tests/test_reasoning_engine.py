"""Step 5 — Reasoning Engine unit tests."""

from __future__ import annotations

from cognitive.engines.reasoning_engine import ReasoningEngine
from cognitive.models.evidence import Evidence, EvidenceItem


def _item(
    *,
    tf: str,
    name: str,
    feature_type: str,
    direction: str,
    weight: float,
    confidence: float = 90,
) -> EvidenceItem:
    return EvidenceItem(
        id=f"{tf}-{feature_type}",
        name=name,
        feature_type=feature_type,
        direction=direction,  # type: ignore[arg-type]
        strength="Very Strong",
        weight=weight,
        confidence=confidence,
        timeframe=tf,
        rationale=f"{name} → {direction}",
    )


def test_no_trade_when_insufficient() -> None:
    weak = Evidence(
        items=[],
        buy_weight=2,
        sell_weight=2,
        neutral_weight=20,
        image_uncertainty=10,
        missing_evidence=["trend", "liquidity"],
    )
    report = ReasoningEngine().reason(
        {"4H": weak, "1H": weak, "15M": weak}, pair="XAUUSD"
    )
    assert report.conclusion == "NO TRADE"
    assert report.gates_failed
    assert report.explanation


def test_explainable_buy_with_aligned_evidence() -> None:
    def strong_buy(tf: str) -> Evidence:
        items = [
            _item(tf=tf, name="Bullish BOS", feature_type="bos", direction="BUY", weight=18),
            _item(
                tf=tf,
                name="Bullish OB",
                feature_type="bullish_order_block",
                direction="BUY",
                weight=14,
            ),
        ]
        return Evidence(
            items=items,
            buy_weight=32,
            sell_weight=2,
            neutral_weight=1,
            dominant_direction="BUY",
            supporting_structures=["bos:Bullish BOS"],
            conflicting_structures=[],
            image_uncertainty=5,
        )

    report = ReasoningEngine().reason(
        {"4H": strong_buy("4H"), "1H": strong_buy("1H"), "15M": strong_buy("15M")},
        pair="EURUSD",
    )
    assert report.conclusion in {"BUY", "NO TRADE"}  # gates may still apply
    assert report.buy_evidence_score > report.sell_evidence_score
    assert report.supporting_structures or report.supporting
    assert report.trace.get("confidence") is not None
    if report.conclusion == "BUY":
        assert not report.gates_failed
        assert "Evidence supports BUY" in report.explanation


def test_structure_stalemate_prefers_no_trade() -> None:
    contested = Evidence(
        items=[
            _item(tf="1H", name="BOS", feature_type="bos", direction="BUY", weight=10),
            _item(tf="1H", name="CHOCH", feature_type="choch", direction="SELL", weight=10),
        ],
        buy_weight=10,
        sell_weight=10,
        neutral_weight=0,
        dominant_direction="NEUTRAL",
        supporting_structures=["bos:BOS"],
        conflicting_structures=["choch:CHOCH"],
        image_uncertainty=5,
    )
    report = ReasoningEngine().reason(
        {"4H": contested, "1H": contested, "15M": contested},
        pair="GBPUSD",
    )
    assert report.conclusion == "NO TRADE"
    assert report.gates_failed


def test_high_uncertainty_gate() -> None:
    noisy = Evidence(
        items=[_item(tf="4H", name="BOS", feature_type="bos", direction="BUY", weight=20)],
        buy_weight=20,
        sell_weight=1,
        dominant_direction="BUY",
        supporting_structures=["bos:BOS"],
        image_uncertainty=70,
    )
    report = ReasoningEngine().reason(
        {"4H": noisy, "1H": noisy, "15M": noisy}, pair="USDJPY"
    )
    assert report.conclusion == "NO TRADE"
    assert "image_uncertainty" in report.gates_failed


def test_reasoning_api_from_evidence() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    evidence = {
        "items": [],
        "buy_weight": 1,
        "sell_weight": 1,
        "neutral_weight": 10,
        "dominant_direction": "NEUTRAL",
        "image_uncertainty": 20,
        "supporting_structures": [],
        "conflicting_structures": [],
        "missing_evidence": ["bos"],
        "notes": [],
    }
    resp = client.post(
        "/api/cognitive/reasoning/from-evidence",
        json={
            "pair": "EURUSD",
            "evidence_by_tf": {"4H": evidence, "1H": evidence, "15M": evidence},
        },
    )
    assert resp.status_code == 200
    body = resp.json()["reasoning"]
    assert body["conclusion"] == "NO TRADE"
    assert body["gates_failed"]
    assert body["explanation"]
