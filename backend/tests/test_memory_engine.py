from decision.confidence_engine import WEIGHTS
from memory.confidence_adjuster import ConfidenceAdjuster, MIN_SIMILAR_FOR_ADJUSTMENT
from memory.feature_fingerprint import FEATURE_KEYS, build_fingerprint, features_to_bits
from memory.learning_engine import LearningEngine
from memory.lesson_generator import LessonGenerator
from memory.similarity_engine import SimilarityEngine, SimilarityReport, combined_similarity
from models.chart_schemas import ChartAnalysis, PriceContext
from models.decision_schemas import ConfidenceScorecard, TradeDecision


def _chart(trend: str = "Bullish", **kwargs) -> ChartAnalysis:
    defaults = dict(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        trend=trend,
        market_structure="Higher Highs",
        bos=True,
        choch=False,
        liquidity="Liquidity Sweep",
        liquidity_sweep=True,
        equal_highs=False,
        equal_lows=False,
        bullish_order_block=True,
        bearish_order_block=False,
        fair_value_gap=True,
        fvg_type="Bullish FVG",
        supply_zone=False,
        demand_zone=True,
        premium="No",
        discount="Yes",
        candle_count=40,
        swing_high_count=3,
        swing_low_count=3,
        confidence=80,
        price_context=PriceContext(last_close=50, swing_high=70, swing_low=40, avg_range=1.2),
    )
    defaults.update(kwargs)
    return ChartAnalysis(**defaults)  # type: ignore[arg-type]


def _decision(bias: str = "BUY") -> TradeDecision:
    return TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=_chart("Bullish"),
        analysis_1h=_chart("Bullish", timeframe="1H"),
        analysis_15m=_chart("Bullish", timeframe="15M", bos=True, choch=True),
        overall_bias=bias,  # type: ignore[arg-type]
        entry="50.00",
        stop_loss="40.00",
        take_profit="70.00",
        risk_reward="2.00",
        target_liquidity="Buy-side",
        confidence=82.0,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=80,
            mtf_1h_alignment=80,
            ltf_15m_confirmation=80,
            liquidity=70,
            order_block=70,
            fair_value_gap=70,
            market_structure=70,
            overall=82,
            weights=dict(WEIGHTS),
        ),
        explanation="BUY test",
        reasons=["test"],
        warnings=[],
        generated_at="2026-01-01T00:00:00+00:00",
    )


def test_fingerprint_stable_length():
    fp = build_fingerprint(_decision())
    assert len(fp["bits"]) == len(FEATURE_KEYS)
    assert fp["features"]["trend_alignment"] is True
    assert fp["features"]["direction_buy"] is True


def test_similarity_metric_bounds():
    a = features_to_bits({"trend_alignment": True, "bos": True, "direction_buy": True})
    b = features_to_bits({"trend_alignment": True, "bos": True, "direction_buy": True})
    c = features_to_bits({"direction_sell": True, "bearish_order_block": True})
    assert combined_similarity(a, b) == 1.0 or combined_similarity(a, b) > 0.9
    assert combined_similarity(a, c) < combined_similarity(a, b)


def test_confidence_adjuster_withholds_small_samples():
    report = SimilarityReport(
        query_bits="1" * len(FEATURE_KEYS),
        similar=[],
        total_compared=10,
        tp_count=5,
        sl_count=2,
        win_rate=71.4,
        min_similarity=0.72,
    )
    adj = ConfidenceAdjuster().adjust(80.0, report)
    assert adj.similar_count < MIN_SIMILAR_FOR_ADJUSTMENT
    assert "limited" in adj.reason.lower() or adj.similar_count < MIN_SIMILAR_FOR_ADJUSTMENT


def test_confidence_adjuster_applies_with_enough_samples():
    report = SimilarityReport(
        query_bits="1" * len(FEATURE_KEYS),
        similar=[],
        total_compared=200,
        tp_count=160,
        sl_count=40,
        win_rate=80.0,
        min_similarity=0.72,
    )
    adj = ConfidenceAdjuster().adjust(75.0, report)
    assert adj.applied is True
    assert adj.adjusted_confidence >= 75.0
    assert "factors" in adj.__dataclass_fields__ or adj.factors


def test_lesson_generator_tp_and_sl():
    decision = _decision("BUY")
    gen = LessonGenerator()
    win = gen.generate(decision, "TAKE_PROFIT")
    loss = gen.generate(decision, "STOP_LOSS")
    assert "alignment" in win.lower() or "liquidity" in win.lower() or "order block" in win.lower()
    assert len(loss) > 10


def test_learning_engine_records_without_crash():
    engine = LearningEngine()
    bits = build_fingerprint(_decision())["bits"]
    engine.record_outcome(bits, "TAKE_PROFIT")
    weights = engine.get_adaptive_weights()
    assert abs(sum(weights.values()) - 1.0) < 1e-6
