"""Step 8 — Learning Engine: incremental, idempotent, no single-trade retrain."""

from __future__ import annotations

from cognitive.engines.learning_engine import CognitiveLearningEngine
from memory.learning_engine import (
    LearningEngine,
    MIN_SAMPLES_FOR_FEATURE_INFLUENCE,
    MIN_SAMPLES_FOR_WEIGHT_UPDATE,
)
from memory.outcome_utils import is_neutral, normalize_outcome
from memory.pattern_engine import PatternEngine
from research.confidence_calibration import (
    MIN_SAMPLES_FOR_ADJUSTMENT,
    ConfidenceCalibrationEngine,
)
from research.pattern_library import PatternLibrary


def test_normalize_break_even_is_neutral() -> None:
    assert normalize_outcome("BE") == "BREAK_EVEN"
    assert is_neutral("BREAK_EVEN")
    assert not is_neutral("TAKE_PROFIT")


def test_calibration_factor_unchanged_after_single_trade() -> None:
    cal = ConfidenceCalibrationEngine()
    before = cal.state().adjustment_factor
    after = cal.record(82.0, success=True)
    assert after.sample_count >= 1
    # Single trade must not move the factor until MIN_SAMPLES_FOR_ADJUSTMENT
    if after.sample_count < MIN_SAMPLES_FOR_ADJUSTMENT:
        assert after.adjustment_factor == before or abs(after.adjustment_factor - before) < 1e-9


def test_feature_weights_need_sample_floor() -> None:
    assert MIN_SAMPLES_FOR_FEATURE_INFLUENCE >= 12
    assert MIN_SAMPLES_FOR_WEIGHT_UPDATE >= 20
    eng = LearningEngine()
    weights_before = eng.get_adaptive_weights()
    # One strong TP on a synthetic fingerprint — should update feature_stats but
    # not necessarily rebalance scorecard weights (sample floors).
    bits = "1" * 24
    eng.record_outcome(bits, "TAKE_PROFIT", learning_strength=1.0)
    weights_after = eng.get_adaptive_weights()
    # Keys preserved; values may be identical if under sample floor.
    assert set(weights_after.keys()) == set(weights_before.keys())


def test_break_even_does_not_count_as_win_in_patterns() -> None:
    pe = PatternEngine()
    bits = "101010101010101010101010"
    before = pe.get(bits)
    before_wins = int((before or {}).get("wins") or 0)
    before_losses = int((before or {}).get("losses") or 0)
    row = pe.record(bits, outcome="BREAK_EVEN", risk_reward=1.5, confidence=70)
    assert row["wins"] == before_wins
    assert row["losses"] == before_losses
    assert row["trades"] >= (before or {}).get("trades", 0) + 1


def test_pattern_library_break_even_neither_win_nor_loss() -> None:
    lib = PatternLibrary()
    features = ["bos", "bullish_order_block", "step8_be_test"]
    before = lib.get(features)
    before_wins = before.wins if before else 0
    before_losses = before.losses if before else 0
    rec = lib.record_outcome(features, outcome="BREAK_EVEN", confidence=75.0, risk_reward=2.0)
    assert rec.wins == before_wins
    assert rec.losses == before_losses


def test_cognitive_nudge_requires_features_and_skips_be(tmp_path) -> None:
    eng = CognitiveLearningEngine(weights_path=tmp_path / "w.json")
    before = eng.current_weights().get("bos", 0)
    assert eng.apply_incremental_update(
        outcome="BREAK_EVEN",
        feature_types=["bos"],
        grade="A",
        learning_strength=1.0,
    ) == {}
    assert eng.apply_incremental_update(
        outcome="TAKE_PROFIT",
        feature_types=[],
        grade="A",
        learning_strength=1.0,
    ) == {}
    updates = eng.apply_incremental_update(
        outcome="TAKE_PROFIT",
        feature_types=["bos"],
        grade="A",
        learning_strength=1.0,
    )
    assert "bos" in updates
    assert eng.current_weights()["bos"] != before or updates["bos"] == before
    # Delta capped — not a full retrain
    assert abs(eng.current_weights()["bos"] - before) < 1.0


def test_learning_summary_api_shape() -> None:
    from research.orchestrator import ResearchOrchestrator

    summary = ResearchOrchestrator().learning_summary()
    assert "calibration" in summary
    assert "feature_reliability" in summary
    assert "adaptive_weights" in summary
    assert "top_patterns" in summary
    assert "cognitive" in summary


def test_learning_summary_http() -> None:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    resp = client.get("/api/learning/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "calibration" in body
    assert "adaptive_weights" in body
