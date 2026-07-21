"""Unit tests for every Knowledge Engine v1.0 concept rule."""

from __future__ import annotations

from cognitive.models.features import CognitiveFeature, FeatureCollection
from cognitive.models.market import MarketModel
from core.models.chart import Candle, Trend
from knowledge.catalog.v1_0 import VERSION, build_concepts, build_relationships
from knowledge.engine import KnowledgeEngine
from knowledge.registry import get_registry
from knowledge.validator import KnowledgeValidator, build_context
from knowledge.versioning import CURRENT_VERSION, list_versions


def test_current_version_is_1_0() -> None:
    assert CURRENT_VERSION == "1.0"
    assert VERSION == "1.0"
    assert "1.0" in list_versions()


def test_all_required_concepts_present() -> None:
    required = {
        "trend",
        "bullish_trend",
        "bearish_trend",
        "range",
        "higher_high",
        "higher_low",
        "lower_high",
        "lower_low",
        "bos",
        "choch",
        "bullish_order_block",
        "bearish_order_block",
        "bullish_fvg",
        "bearish_fvg",
        "liquidity",
        "internal_liquidity",
        "external_liquidity",
        "liquidity_sweep",
        "supply_zone",
        "demand_zone",
        "premium",
        "discount",
        "impulse_move",
        "retracement",
        "mitigation",
    }
    ids = {c.id for c in build_concepts()}
    assert required.issubset(ids)


def test_every_concept_has_valid_and_invalid_examples() -> None:
    for concept in build_concepts():
        valids = [e for e in concept.examples if e.valid]
        invalids = [e for e in concept.examples if not e.valid]
        assert valids, f"{concept.id} missing valid example"
        assert invalids, f"{concept.id} missing invalid example"
        assert concept.version == "1.0"
        assert concept.definition
        assert concept.validation_rules


def test_every_concept_example_validates_as_expected() -> None:
    engine = KnowledgeEngine("1.0")
    for concept in engine.list_concepts():
        for example in concept.examples:
            result = engine.validate_concept(concept.id, example.context)
            if example.valid:
                assert result.status == "valid", (
                    f"{concept.id} / {example.title}: expected valid, got {result.status} "
                    f"{result.failed_required} {result.triggered_invalid} {result.notes}"
                )
            else:
                assert result.status in {"invalid", "unknown"}, (
                    f"{concept.id} / {example.title}: expected invalid/unknown, got {result.status}"
                )


def test_relationships_do_not_guarantee_trades() -> None:
    for rel in build_relationships():
        assert rel.strengthens_trade is False
        assert rel.source and rel.target
        # Relationships must not imply a trade guarantee
        blob = f"{rel.description} {rel.notes}".lower()
        assert (
            "guarantee" in blob
            or "does not" in blob
            or "may" in blob
            or "not" in blob
        ), f"{rel.source}->{rel.target} notes must clarify non-guarantee"


def test_named_prefer_rules_are_soft() -> None:
    from knowledge.conditions import evaluate_named_rule

    ok, _, soft = evaluate_named_rule("prefer_hh_hl", {"has_higher_high": False})
    assert soft is True
    assert ok is False
    ok2, _, soft2 = evaluate_named_rule("require_bullish_direction", {"trend": {"direction": "Bullish"}})
    assert soft2 is False
    assert ok2 is True


def test_unknown_version_api_returns_404() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.get("/api/knowledge/concepts", params={"version": "99.9"})
    assert resp.status_code == 404
    assert "Unknown knowledge version" in resp.json()["detail"]


def test_validate_features_endpoint() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    payload = {
        "features": {
            "timeframe": "1H",
            "pair": "EURUSD",
            "features": [],
            "missing": [],
            "warnings": [],
        },
        "market": None,
    }
    resp = client.post("/api/knowledge/validate/features", json=payload)
    assert resp.status_code == 200
    assert resp.json()["knowledge_version"] == "1.0"


def test_bos_unknown_without_trend() -> None:
    engine = KnowledgeEngine()
    result = engine.validate_concept(
        "bos",
        {"market_usable": True, "bos": True, "trend": {"direction": "Unknown", "confidence": 0}},
    )
    assert result.status in {"invalid", "unknown"}


def test_incomplete_market_returns_unknown() -> None:
    engine = KnowledgeEngine()
    result = engine.validate_concept(
        "liquidity_sweep",
        {"market_usable": False, "has_liquidity_sweep": True},
    )
    assert result.status == "unknown"


def test_validate_features_filters_invalid() -> None:
    market = MarketModel(
        status="ok",
        timeframe="1H",
        pair="EURUSD",
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
            for i in range(8)
        ],
        trend=Trend(direction="Bullish", confidence=90),
        bos=True,
    )
    features = FeatureCollection(
        timeframe="1H",
        pair="EURUSD",
        features=[
            CognitiveFeature(
                name="Bullish BOS",
                feature_type="bos",
                confidence=90,
                direction_hint="BUY",
                timeframe="1H",
            ),
            CognitiveFeature(
                name="Fake sweep",
                feature_type="liquidity_sweep",
                confidence=90,
                direction_hint="BUY",
                timeframe="1H",
            ),
        ],
    )
    # No liquidity sweep on market — feature injects has_liquidity_sweep via feature type
    # so sweep may validate. Force rejection by low confidence on a concept with min_detect.
    features.features[1] = features.features[1].model_copy(update={"confidence": 10})
    validated = KnowledgeEngine().validate_features(features, market)
    assert any(f.feature_type == "bos" for f in validated.features)
    assert not any(f.feature_type == "liquidity_sweep" for f in validated.features)
    assert any("liquidity_sweep" in m for m in validated.missing)


def test_version_isolation_registry() -> None:
    r1 = get_registry("1.0")
    assert r1.version == "1.0"
    assert r1.get_concept("bos") is not None
    # Future versions must not delete 1.0
    assert "1.0" in list_versions()


def test_engine_api_surfaces() -> None:
    eng = KnowledgeEngine()
    assert eng.get_meta().concept_count >= 25
    assert eng.get_concept("choch") is not None
    assert eng.get_relationships("bos")
    meta = eng.rule_metadata()
    assert meta["knowledge_version"] == "1.0"
    assert len(meta["concepts"]) >= 25


def test_build_context_from_market() -> None:
    market = MarketModel(
        status="ok",
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
        trend=Trend(direction="Bearish", confidence=70, pullback=True),
        choch=True,
        premium="Yes",
        discount="No",
    )
    market.candles = [c.model_copy(update={"index": i}) for i, c in enumerate(market.candles)]
    ctx = build_context(market)
    assert ctx["choch"] is True
    assert ctx["has_retracement"] is True
    assert ctx["premium"] == "Yes"


def test_knowledge_api_import() -> None:
    from api.knowledge import router

    paths = {getattr(r, "path", None) for r in router.routes}
    assert "/knowledge/concepts" in paths
    assert "/knowledge/validate" in paths
    assert "/knowledge/validate/features" in paths


def test_brain_validates_via_knowledge_not_raw_flags() -> None:
    """Brain validated_concepts must come from KnowledgeEngine, not raw CV flags."""
    from brain.coordinator import AIBrain
    from brain.models import EngineBundle
    from cognitive.models.decision import CognitiveDecision
    from cognitive.models.reasoning import ReasoningReport
    from models.chart_schemas import ChartAnalysis
    from models.decision_schemas import ConfidenceScorecard, TradeDecision
    from models.schemas import utc_now_iso

    market = MarketModel(
        status="ok",
        timeframe="1H",
        pair="EURUSD",
        candles=[
            Candle(
                index=i,
                open=1.0 + i * 0.01,
                high=1.02 + i * 0.01,
                low=0.99 + i * 0.01,
                close=1.01 + i * 0.01,
                bullish=True,
                body_size=0.01,
                upper_wick=0.01,
                lower_wick=0.01,
            )
            for i in range(10)
        ],
        trend=Trend(direction="Bullish", confidence=85),
        bos=True,
        choch=False,
    )
    chart = ChartAnalysis(
        status="ok",
        pair="EURUSD",
        timeframe="1H",
        trend="Bullish",
        market_structure="Higher Highs",
        bos=True,
        confidence=80,
    )
    provisional = TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart.model_copy(update={"timeframe": "4H"}),
        analysis_1h=chart,
        analysis_15m=chart.model_copy(update={"timeframe": "15M"}),
        overall_bias="NO TRADE",
        entry="—",
        stop_loss="—",
        take_profit="—",
        risk_reward="—",
        target_liquidity="—",
        confidence=40.0,
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
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=0,
        sell_evidence_score=0,
        conclusion="NO TRADE",
        confidence=40,
        narrative=["test"],
    )
    cognitive = CognitiveDecision(
        pair="EURUSD",
        recommendation="NO TRADE",
        confidence=40.0,
        trade_grade="F",
        explanation="test",
    )
    brain = AIBrain()
    bundle = brain._build_bundle(
        markets={"1H": market},
        report=report,
        cognitive=cognitive,
        provisional=provisional,
    )
    assert isinstance(bundle, EngineBundle)
    for item in bundle.validated_concepts:
        assert ":" in item
        concept_id = item.split(":", 1)[1]
        assert brain.knowledge.get_concept(concept_id) is not None
    if "1H:bos" in bundle.validated_concepts:
        assert market.bos is True
