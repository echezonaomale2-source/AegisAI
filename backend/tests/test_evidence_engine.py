"""Step 4 — Evidence Engine unit tests."""

from __future__ import annotations

from cognitive.engines.evidence_engine import EvidenceEngine, strength_from_confidence
from cognitive.models.features import CognitiveFeature, FeatureCollection


def test_strength_bands() -> None:
    assert strength_from_confidence(95) == "Very Strong"
    assert strength_from_confidence(80) == "Strong"
    assert strength_from_confidence(60) == "Medium"
    assert strength_from_confidence(40) == "Weak"
    assert strength_from_confidence(10) == "Very Weak"


def test_evaluate_records_direction_weight_strength_confidence() -> None:
    features = FeatureCollection(
        timeframe="4H",
        pair="EURUSD",
        features=[
            CognitiveFeature(
                name="Bullish BOS",
                feature_type="bos",
                confidence=94,
                direction_hint="BUY",
                timeframe="4H",
                supporting_candles=[3, 4, 5],
            ),
            CognitiveFeature(
                name="Bullish OB",
                feature_type="bullish_order_block",
                confidence=90,
                direction_hint="BUY",
                timeframe="4H",
            ),
        ],
    )
    evidence = EvidenceEngine().evaluate(features, image_quality=92)
    assert evidence.buy_weight > evidence.sell_weight
    assert evidence.dominant_direction == "BUY"
    assert evidence.supporting_structures
    assert not evidence.conflicting_structures
    item = evidence.items[0]
    assert item.direction == "BUY"
    assert item.weight > 0
    assert item.strength == "Very Strong"
    assert item.confidence == 94
    assert item.supporting_structures
    assert item.trace_id
    assert item.supporting_candles == [3, 4, 5]


def test_conflicting_structures_detected() -> None:
    features = FeatureCollection(
        timeframe="1H",
        pair="EURUSD",
        features=[
            CognitiveFeature(
                name="Bullish BOS",
                feature_type="bos",
                confidence=92,
                direction_hint="BUY",
                timeframe="1H",
            ),
            CognitiveFeature(
                name="Bearish CHOCH",
                feature_type="choch",
                confidence=88,
                direction_hint="SELL",
                timeframe="1H",
            ),
            CognitiveFeature(
                name="Bearish OB",
                feature_type="bearish_order_block",
                confidence=85,
                direction_hint="SELL",
                timeframe="1H",
            ),
        ],
    )
    evidence = EvidenceEngine().evaluate(features, image_quality=95)
    assert evidence.conflicting_structures or evidence.supporting_structures
    # Both sides present → one side is support, other conflict
    assert evidence.buy_weight > 0 and evidence.sell_weight > 0
    assert evidence.dominant_direction in {"BUY", "SELL"}
    if evidence.dominant_direction == "BUY":
        assert any("choch" in s or "bearish" in s.lower() for s in evidence.conflicting_structures)
    else:
        assert any("bos" in s for s in evidence.conflicting_structures)


def test_unknown_hint_is_neutral_never_guess() -> None:
    features = FeatureCollection(
        timeframe="15M",
        pair="XAUUSD",
        features=[
            CognitiveFeature(
                name="Ambiguous",
                feature_type="liquidity",
                confidence=70,
                direction_hint="Unknown",  # type: ignore[arg-type]
                timeframe="15M",
            )
        ],
        missing=["bos"],
    )
    evidence = EvidenceEngine().evaluate(features)
    assert evidence.items[0].direction == "NEUTRAL"
    assert evidence.dominant_direction == "NEUTRAL"
    assert "bos" in evidence.missing_evidence


def test_evidence_report_summary() -> None:
    features = FeatureCollection(
        timeframe="4H",
        pair="EURUSD",
        features=[
            CognitiveFeature(
                name="Bullish BOS",
                feature_type="bos",
                confidence=90,
                direction_hint="BUY",
                timeframe="4H",
            )
        ],
    )
    eng = EvidenceEngine()
    evidence = eng.evaluate(features)
    report = eng.report(evidence, timeframe="4H", pair="EURUSD")
    assert report.dominant_direction == "BUY"
    assert report.item_count == 1
    assert "BUY=" in report.summary
    assert report.supporting_structures


def test_evidence_api_endpoint() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.post(
        "/api/cognitive/evidence/evaluate",
        json={
            "pair": "EURUSD",
            "image_quality": 90,
            "features": {
                "timeframe": "1H",
                "pair": "EURUSD",
                "features": [
                    {
                        "name": "Bullish BOS",
                        "feature_type": "bos",
                        "confidence": 88,
                        "direction_hint": "BUY",
                        "timeframe": "1H",
                    }
                ],
                "missing": [],
                "warnings": [],
            },
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["evidence"]["dominant_direction"] == "BUY"
    assert body["report"]["item_count"] == 1
    assert body["report"]["summary"]
