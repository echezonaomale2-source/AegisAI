"""Phase 11 — market data verification unit tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from brain.coordinator import AIBrain
from verification.confidence import influence_from_match
from verification.discrepancy import DiscrepancyReporter
from verification.engine import VerificationEngine
from verification.models import (
    ChartVisualSnapshot,
    Discrepancy,
    MarketDataSnapshot,
    OHLCCandle,
)
from verification.provider import (
    InMemoryMarketDataProvider,
    NullMarketDataProvider,
    make_ohlc_series,
)

# Reuse brain test fixtures
from tests.test_ai_brain import _bundle, _cognitive, _provisional, _report


def _bullish_closes(n: int = 20, start: float = 1.1000) -> list[float]:
    return [start + i * 0.0004 for i in range(n)]


def _bearish_closes(n: int = 20, start: float = 1.1080) -> list[float]:
    return [start - i * 0.0004 for i in range(n)]


def _visual_bullish(**overrides) -> ChartVisualSnapshot:
    closes = _bullish_closes()
    base = ChartVisualSnapshot(
        pair="EURUSD",
        timeframe="4H",
        trend="Bullish",
        structure_label="HH",
        recent_high=max(closes),
        recent_low=min(closes),
        swing_highs=[closes[-1], closes[-5]],
        swing_lows=[closes[-3], closes[-7]],
        candle_closes=closes,
        candle_count=len(closes),
        image_quality=85,
        captured_at=datetime.now(timezone.utc),
    )
    return base.model_copy(update=overrides)


def _market_from_closes(
    closes: list[float],
    *,
    pair: str = "EURUSD",
    timeframe: str = "4H",
    as_of: datetime | None = None,
) -> MarketDataSnapshot:
    candles = make_ohlc_series(closes)
    # Align high/low to series extremes for fair high/low checks
    hi = max(c.high for c in candles)
    lo = min(c.low for c in candles)
    # Expand last candle extremes so recent_high/low from visual match
    candles[-1] = candles[-1].model_copy(update={"high": max(hi, closes[-1]), "low": min(lo, closes[0])})
    return MarketDataSnapshot(
        pair=pair,
        timeframe=timeframe,
        candles=candles,
        as_of=as_of or datetime.now(timezone.utc),
        provider_name="in_memory",
    )


def test_screenshot_only_null_provider():
    engine = VerificationEngine(provider=NullMarketDataProvider())
    summary = engine.verify(_visual_bullish())
    assert summary.status == "screenshot_only"
    assert summary.screenshot_only is True
    assert summary.influence_on_confidence == 0.0
    assert any("screenshots only" in w.lower() for w in summary.warnings)


def test_screenshot_plus_matching_market_data():
    closes = _bullish_closes()
    visual = _visual_bullish(
        recent_high=max(c.high for c in make_ohlc_series(closes)),
        recent_low=min(c.low for c in make_ohlc_series(closes)),
        candle_closes=closes,
    )
    market = _market_from_closes(closes)
    # Align visual extremes exactly to market
    visual = visual.model_copy(
        update={
            "recent_high": max(c.high for c in market.candles),
            "recent_low": min(c.low for c in market.candles),
        }
    )
    engine = VerificationEngine(provider=NullMarketDataProvider())
    summary = engine.verify(visual, market)
    assert summary.status in {"verified_match", "verified_partial"}
    assert summary.screenshot_only is False
    assert summary.significant_disagreement is False
    assert summary.influence_on_confidence >= 0


def test_screenshot_plus_conflicting_market_data():
    visual = _visual_bullish()
    market = _market_from_closes(_bearish_closes(), pair="EURUSD", timeframe="4H")
    engine = VerificationEngine(provider=NullMarketDataProvider())
    summary = engine.verify(visual, market)
    assert summary.status == "verified_conflict"
    assert summary.significant_disagreement is True
    assert summary.influence_on_confidence < 0
    kinds = {d.kind for d in summary.discrepancies}
    assert "trend_mismatch" in kinds
    assert any("disagreement" in w.lower() or "trend" in w.lower() for w in summary.warnings)


def test_missing_provider_unavailable_snapshot():
    provider = InMemoryMarketDataProvider()  # empty → available() False
    engine = VerificationEngine(provider=provider)
    summary = engine.verify(_visual_bullish())
    assert summary.status == "screenshot_only"
    assert summary.influence_on_confidence == 0.0


def test_network_failure_does_not_fail_analysis():
    provider = InMemoryMarketDataProvider(
        snapshots={
            ("EURUSD", "4H"): _market_from_closes(_bullish_closes()),
        },
        fail_network=True,
    )
    engine = VerificationEngine(provider=provider)
    # available() is False when fail_network — still safe
    assert provider.available() is False
    summary = engine.verify(_visual_bullish())
    assert summary.status == "screenshot_only"

    # Force available path with raising fetch via subclass
    class Flaky(InMemoryMarketDataProvider):
        def available(self) -> bool:
            return True

        def fetch(self, pair, timeframe, *, end_time=None, limit=100):
            raise ConnectionError("timeout")

    flaky = Flaky(
        snapshots={("EURUSD", "4H"): _market_from_closes(_bullish_closes())},
    )
    engine2 = VerificationEngine(provider=flaky)
    summary2 = engine2.verify(_visual_bullish())
    assert summary2.status in {"screenshot_only", "unavailable"}
    assert summary2.screenshot_only is True


def test_old_screenshot_discrepancy():
    old = datetime.now(timezone.utc) - timedelta(hours=72)
    visual = _visual_bullish(captured_at=old)
    market = _market_from_closes(
        _bullish_closes(),
        as_of=datetime.now(timezone.utc),
    )
    visual = visual.model_copy(
        update={
            "recent_high": max(c.high for c in market.candles),
            "recent_low": min(c.low for c in market.candles),
            "candle_closes": [c.close for c in market.candles],
        }
    )
    engine = VerificationEngine(provider=NullMarketDataProvider())
    summary = engine.verify(visual, market)
    kinds = {d.kind for d in summary.discrepancies}
    assert "image_too_old" in kinds


def test_pair_and_timeframe_mismatch():
    visual = _visual_bullish(pair="EURUSD", timeframe="4H")
    market = _market_from_closes(_bullish_closes(), pair="GBPUSD", timeframe="1H")
    engine = VerificationEngine(provider=NullMarketDataProvider())
    summary = engine.verify(visual, market)
    kinds = {d.kind for d in summary.discrepancies}
    assert "pair_mismatch" in kinds
    assert "timeframe_mismatch" in kinds
    assert summary.influence_on_confidence < 0


def test_discrepancy_reporter_persists(tmp_path: Path):
    reporter = DiscrepancyReporter(root=tmp_path)
    engine = VerificationEngine(provider=NullMarketDataProvider(), reporter=reporter)
    visual = _visual_bullish()
    market = _market_from_closes(_bearish_closes())
    summary = engine.verify(visual, market, persist=True, trade_id="t-1")
    assert summary.has_discrepancies
    files = list(tmp_path.glob("*.json"))
    assert len(files) == 1
    recent = reporter.list_recent()
    assert len(recent) == 1
    assert recent[0]["trade_id"] == "t-1"


def test_confidence_influence_helpers():
    assert (
        influence_from_match(
            status="screenshot_only",
            match_score=0,
            discrepancies=[],
            significant=False,
        )
        == 0.0
    )
    boost = influence_from_match(
        status="verified_match",
        match_score=95,
        discrepancies=[],
        significant=False,
    )
    assert boost > 0
    penalty = influence_from_match(
        status="verified_conflict",
        match_score=20,
        discrepancies=[
            Discrepancy(kind="trend_mismatch", severity="high", message="x"),
            Discrepancy(kind="pair_mismatch", severity="high", message="y"),
        ],
        significant=True,
    )
    assert penalty <= -10


def test_brain_screenshot_only_warning():
    brain = AIBrain(market_provider=NullMarketDataProvider())
    rec = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(confidence=85),
        report=_report(),
        cognitive=_cognitive(),
    )
    assert rec.verification is not None
    assert rec.verification.screenshot_only is True
    assert any("screenshot" in w.lower() for w in rec.warnings)


def test_brain_matching_verification_boosts_or_holds_confidence():
    closes = _bullish_closes()
    market = _market_from_closes(closes)
    visual = _visual_bullish(
        recent_high=max(c.high for c in market.candles),
        recent_low=min(c.low for c in market.candles),
        candle_closes=closes,
    )
    engine = VerificationEngine(provider=NullMarketDataProvider())
    verification = engine.verify(visual, market)

    brain = AIBrain(market_provider=NullMarketDataProvider())
    base_conf = 80.0
    rec = brain.decide_from_bundle(
        _bundle(),
        provisional=_provisional(confidence=base_conf),
        report=_report(buy=80, sell=20),
        cognitive=_cognitive(),
        verification=verification,
    )
    assert rec.verification is not None
    assert rec.verification.status in {"verified_match", "verified_partial"}
    assert rec.verification.influence_on_confidence >= 0
    assert rec.confidence >= base_conf


def test_brain_conflict_reduces_confidence():
    closes_bear = _bearish_closes()
    market = _market_from_closes(closes_bear)
    provider = InMemoryMarketDataProvider()
    provider.put(market)
    brain = AIBrain(market_provider=provider)

    from brain.models import EngineBundle

    vision = {
        "4H": {
            "status": "ok",
            "quality": 90,
            "trend": "Bullish",
            "structure": "HH",
            "bos": True,
            "candle_closes": _bullish_closes(),
            "candle_count": 20,
            "recent_high": 1.12,
            "recent_low": 1.10,
        }
    }
    bundle = EngineBundle(
        pair="EURUSD",
        timeframes={"4H": "4H"},
        vision_summaries=vision,
        validated_concepts=["4H:bos"],
        provisional_bias="BUY",
        provisional_confidence=88,
    )
    rec = brain.decide_from_bundle(
        bundle,
        provisional=_provisional(confidence=88.0),
        report=_report(buy=85, sell=15),
        cognitive=_cognitive(),
    )
    assert rec.verification is not None
    assert rec.verification.influence_on_confidence < 0
    assert rec.confidence < 88.0
