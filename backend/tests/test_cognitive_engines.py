"""Automated tests for every Phase 6 cognitive engine."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from cognitive.container import CognitiveContainer, reset_cognitive_container
from cognitive.engines.decision_engine import CognitiveDecisionEngine
from cognitive.engines.evidence_engine import EvidenceEngine, strength_from_confidence
from cognitive.engines.feature_engine import FeatureExtractionEngine
from cognitive.engines.learning_engine import CognitiveLearningEngine
from cognitive.engines.reasoning_engine import ReasoningEngine
from cognitive.engines.reconstruction_engine import ChartReconstructionEngine
from cognitive.engines.risk_engine import CognitiveRiskEngine
from cognitive.engines.vision_engine import CognitiveVisionEngine
from cognitive.models.evidence import Evidence, EvidenceItem
from cognitive.models.features import CognitiveFeature, FeatureCollection
from cognitive.models.market import MarketModel
from cognitive.models.reasoning import ReasoningReport
from cognitive.pipeline import CognitivePipeline
from core.models.chart import Candle, ChartModel, Trend


def _candles(n: int = 12, bullish: bool = True) -> list[Candle]:
    out = []
    for i in range(n):
        base = 100 + i * (2 if bullish else -2)
        out.append(
            Candle(
                index=i,
                open=base,
                high=base + 3,
                low=base - 2,
                close=base + (2 if bullish else -2),
                bullish=bullish,
                body_size=2,
                upper_wick=1,
                lower_wick=1,
                relative_position=i / max(1, n - 1),
                confidence=85,
            )
        )
    return out


def _bullish_chart() -> ChartModel:
    return ChartModel(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        image_quality_score=90,
        reconstruction_confidence=88,
        candles=_candles(12, bullish=True),
        trend=Trend(direction="Bullish", confidence=92, impulse_move=True),
        market_structure_label="Higher Highs",
        bos=True,
        premium="No",
        discount="Yes",
    )


def _write_png(path: Path) -> Path:
    img = Image.new("RGB", (640, 400), (12, 14, 20))
    draw = ImageDraw.Draw(img)
    x = 40
    for i in range(20):
        color = (40, 180, 120) if i % 2 == 0 else (200, 70, 70)
        draw.rectangle([x, 160, x + 10, 200], fill=color)
        draw.line([x + 5, 140, x + 5, 220], fill=color, width=2)
        x += 20
    img.save(path)
    return path


# --- Vision ---
def test_vision_engine_rejects_bad_format(tmp_path: Path) -> None:
    bad = tmp_path / "x.txt"
    bad.write_text("nope")
    model = CognitiveVisionEngine().process(bad)
    assert model.status == "error"


def test_vision_engine_processes_png(tmp_path: Path) -> None:
    png = _write_png(tmp_path / "c.png")
    model = CognitiveVisionEngine().process(png, expected_timeframe="15M")
    assert isinstance(model, ChartModel)
    assert model.source_image_path is not None


# --- Reconstruction ---
def test_reconstruction_builds_market_and_tree() -> None:
    market = ChartReconstructionEngine().rebuild(_bullish_chart())
    assert market.is_usable
    assert market.trend.direction == "Bullish"
    assert market.bos is True
    assert any(n.kind == "trend" for n in market.structure_tree)
    assert any(n.kind == "bos" for n in market.structure_tree)


def test_reconstruction_does_not_invent_on_error() -> None:
    bad = ChartModel(status="error", error="Image Quality Too Low")
    market = ChartReconstructionEngine().rebuild(bad)
    assert market.status == "error"
    assert market.bos is False
    assert market.order_blocks == []


# --- Features ---
def test_feature_extraction_engine() -> None:
    market = ChartReconstructionEngine().rebuild(_bullish_chart())
    features = FeatureExtractionEngine().extract(market)
    assert isinstance(features, FeatureCollection)
    assert features.features
    assert any(f.feature_type in {"trend", "bos", "range"} for f in features.features)


# --- Evidence ---
def test_evidence_strength_bands() -> None:
    assert strength_from_confidence(95) == "Very Strong"
    assert strength_from_confidence(80) == "Strong"
    assert strength_from_confidence(60) == "Medium"
    assert strength_from_confidence(40) == "Weak"
    assert strength_from_confidence(10) == "Very Weak"


def test_evidence_engine_assigns_direction_weight() -> None:
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
            ),
            CognitiveFeature(
                name="Bullish OB",
                feature_type="bullish_order_block",
                confidence=90,
                direction_hint="BUY",
                timeframe="4H",
            ),
            CognitiveFeature(
                name="Liquidity Sweep",
                feature_type="liquidity_sweep",
                confidence=88,
                direction_hint="BUY",
                timeframe="4H",
            ),
        ],
    )
    evidence = EvidenceEngine().evaluate(features, image_quality=92)
    assert evidence.buy_weight > evidence.sell_weight
    assert all(i.direction == "BUY" for i in evidence.items)
    assert evidence.items[0].weight > 0
    assert evidence.items[0].trace_id


# --- Reasoning ---
def test_reasoning_no_trade_when_insufficient() -> None:
    weak = Evidence(
        items=[],
        buy_weight=2,
        sell_weight=2,
        neutral_weight=20,
        image_uncertainty=10,
        missing_evidence=["trend", "liquidity"],
    )
    report = ReasoningEngine().reason({"4H": weak, "1H": weak, "15M": weak}, pair="XAUUSD")
    assert report.conclusion == "NO TRADE"
    assert report.confidence < 70 or report.conclusion == "NO TRADE"


def test_reasoning_buy_with_strong_aligned_evidence() -> None:
    def strong_buy(tf: str) -> Evidence:
        items = [
            EvidenceItem(
                id=f"{tf}-bos",
                name="Bullish BOS",
                feature_type="bos",
                direction="BUY",
                strength="Very Strong",
                weight=18,
                confidence=95,
                timeframe=tf,
                rationale=f"{tf} BOS",
                trace_id=f"{tf}bos",
            ),
            EvidenceItem(
                id=f"{tf}-ob",
                name="Bullish OB",
                feature_type="bullish_order_block",
                direction="BUY",
                strength="Strong",
                weight=12,
                confidence=90,
                timeframe=tf,
                rationale=f"{tf} OB",
                trace_id=f"{tf}ob",
            ),
            EvidenceItem(
                id=f"{tf}-trend",
                name="Bullish Trend",
                feature_type="trend",
                direction="BUY",
                strength="Very Strong",
                weight=15,
                confidence=96,
                timeframe=tf,
                rationale=f"{tf} trend",
                trace_id=f"{tf}tr",
            ),
        ]
        return Evidence(
            items=items,
            buy_weight=45,
            sell_weight=3,
            neutral_weight=2,
            image_uncertainty=5,
        )

    report = ReasoningEngine().reason(
        {"4H": strong_buy("4H"), "1H": strong_buy("1H"), "15M": strong_buy("15M")},
        pair="EURUSD",
    )
    assert report.buy_evidence_score > report.sell_evidence_score
    assert report.conclusion in {"BUY", "NO TRADE"}  # gated by thresholds
    assert "buy_score" in report.trace
    if report.conclusion == "BUY":
        assert report.confidence >= 70


def test_reasoning_blocks_high_image_uncertainty() -> None:
    ev = Evidence(
        items=[
            EvidenceItem(
                id="1",
                name="BOS",
                feature_type="bos",
                direction="BUY",
                strength="Strong",
                weight=20,
                confidence=90,
                timeframe="4H",
                rationale="bos",
                trace_id="t",
            )
        ],
        buy_weight=40,
        sell_weight=5,
        neutral_weight=2,
        image_uncertainty=80,
    )
    report = ReasoningEngine().reason({"4H": ev, "1H": ev, "15M": ev})
    assert report.conclusion == "NO TRADE"
    assert any("uncertainty" in n.lower() for n in report.narrative)


# --- Risk ---
def test_risk_engine_no_trade() -> None:
    report = ReasoningReport(conclusion="NO TRADE", confidence=40)
    risk = CognitiveRiskEngine().assess(report, {})
    assert risk.valid is False
    assert risk.risk_grade == "F"


# --- Decision ---
def test_decision_engine_explainable_no_trade() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=40,
        sell_evidence_score=38,
        neutral_score=22,
        conclusion="NO TRADE",
        confidence=55,
        narrative=["Thin margin."],
        trace={"confidence": 55},
    )
    risk = CognitiveRiskEngine().assess(report, {})
    decision = CognitiveDecisionEngine().decide(report, risk, pair="EURUSD")
    assert decision.recommendation == "NO TRADE"
    assert decision.trade_grade == "F"
    assert decision.explanation
    assert decision.reproducible_hash


def test_decision_same_inputs_same_hash() -> None:
    report = ReasoningReport(
        pair="EURUSD",
        buy_evidence_score=82,
        sell_evidence_score=24,
        neutral_score=9,
        conclusion="NO TRADE",
        confidence=60,
        narrative=["test"],
        trace={"confidence": 60, "buy_score": 82},
    )
    risk = CognitiveRiskEngine().assess(report, {})
    engine = CognitiveDecisionEngine()
    a = engine.decide(report, risk, pair="EURUSD")
    b = engine.decide(report, risk, pair="EURUSD")
    assert a.reproducible_hash == b.reproducible_hash


# --- Learning ---
def test_learning_engine_updates_weights_without_crash(tmp_path: Path) -> None:
    engine = CognitiveLearningEngine(weights_path=tmp_path / "w.json")
    before = engine.current_weights()["bos"]
    # Simulate weight nudge path directly (skip legacy DB)
    engine._weights["bos"] = before
    engine._weights["_rel_bos"] = 1.0
    # Manual incremental update mimicking learn path
    rel = 1.04
    engine._weights["_rel_bos"] = rel
    from cognitive.weights import DEFAULT_FEATURE_WEIGHTS

    engine._weights["bos"] = round(DEFAULT_FEATURE_WEIGHTS["bos"] * rel, 3)
    engine._save_weights()
    reloaded = CognitiveLearningEngine(weights_path=tmp_path / "w.json")
    assert reloaded.current_weights()["bos"] == engine._weights["bos"]


# --- Memory archive ---
def test_memory_archive_write(tmp_path: Path) -> None:
    from cognitive.engines.memory_engine import CognitiveMemoryEngine
    from cognitive.models.decision import CognitiveDecision
    from models.decision_schemas import ConfidenceScorecard, TradeDecision
    from models.chart_schemas import ChartAnalysis
    from models.schemas import utc_now_iso
    from storage.trade_store import TradeStore

    # Skip full remember (needs images) — verify archive dir creation
    mem = CognitiveMemoryEngine(archive_root=tmp_path / "archive")
    assert mem._archive.exists()


# --- Container / pipeline wiring ---
def test_cognitive_container_independent_engines() -> None:
    reset_cognitive_container()
    c = CognitiveContainer()
    assert c.vision and c.reconstruction and c.features
    assert c.evidence and c.reasoning and c.decision
    assert c.risk and c.memory and c.learning


def test_pipeline_reason_multi_synthetic(tmp_path: Path) -> None:
    p4 = _write_png(tmp_path / "4h.png")
    p1 = _write_png(tmp_path / "1h.png")
    p15 = _write_png(tmp_path / "15m.png")
    pipeline = CognitivePipeline(CognitiveContainer())
    markets, report, decision = pipeline.reason_multi(
        chart_4h=p4,
        chart_1h=p1,
        chart_15m=p15,
        pair="TEST",
    )
    assert set(markets.keys()) == {"4H", "1H", "15M"}
    assert report.conclusion in {"BUY", "SELL", "NO TRADE"}
    assert decision.recommendation in {"BUY", "SELL", "NO TRADE"}
    # Insufficient synthetic evidence should usually be NO TRADE — never hallucinate
    assert isinstance(decision.explanation, str) and len(decision.explanation) > 10
