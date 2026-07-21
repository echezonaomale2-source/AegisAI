from memory.pattern_engine import PatternEngine, pattern_label_from_bits, pattern_key_from_bits
from memory.performance_engine import PerformanceEngine
from memory.review_engine import ReviewEngine, ReviewScorecard, grade_from_score
from memory.feature_fingerprint import build_fingerprint
from decision.confidence_engine import WEIGHTS
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


def test_grade_mapping():
    assert grade_from_score(95) == "A+"
    assert grade_from_score(86) == "A"
    assert grade_from_score(76) == "B"
    assert grade_from_score(66) == "C"
    assert grade_from_score(52) == "D"
    assert grade_from_score(40) == "F"


def test_review_engine_produces_scorecard_and_critique():
    review = ReviewEngine().review(_decision("BUY"), outcome="TAKE_PROFIT", outcome_chart_path=None)
    assert 0 <= review.scorecard.overall_analysis_quality <= 100
    assert review.grade in {"A+", "A", "B", "C", "D", "F"}
    assert review.critique.strengths
    assert review.critique.weaknesses
    assert "Was my market analysis correct?" in review.questions


def test_performance_engine_learning_gate():
    scorecard = ReviewScorecard(
        market_structure_accuracy=80,
        liquidity_detection_accuracy=80,
        order_block_quality=80,
        fvg_quality=80,
        entry_quality=80,
        stop_loss_placement=80,
        take_profit_placement=80,
        risk_reward_quality=80,
        overall_analysis_quality=80,
    )
    result = PerformanceEngine().classify(scorecard)
    assert result["grade"] == "B"
    assert result["should_influence_learning"] is True


def test_pattern_engine_updates_stats():
    decision = _decision("BUY")
    bits = build_fingerprint(decision)["bits"]
    engine = PatternEngine()
    first = engine.record(bits, outcome="TAKE_PROFIT", risk_reward=2.5, confidence=80)
    second = engine.record(bits, outcome="STOP_LOSS", risk_reward=2.5, confidence=70)
    assert second["trades"] >= first["trades"]
    assert second["wins"] >= 1
    assert second["losses"] >= 1
    assert pattern_key_from_bits(bits)
    assert "BUY" in pattern_label_from_bits(bits) or "HTF" in pattern_label_from_bits(bits)
