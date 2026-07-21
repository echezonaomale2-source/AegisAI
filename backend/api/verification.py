"""Market data verification API — optional OHLC cross-check."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field

from verification.discrepancy import DiscrepancyReporter
from verification.engine import VerificationEngine
from verification.models import (
    ChartVisualSnapshot,
    MarketDataSnapshot,
    OHLCCandle,
    VerificationSummary,
)
from verification.provider import InMemoryMarketDataProvider, NullMarketDataProvider

router = APIRouter(tags=["verification"])
_reporter = DiscrepancyReporter()


class VisualPayload(BaseModel):
    pair: str = "Unknown"
    timeframe: str = "4H"
    trend: str = "Unknown"
    structure_label: str = "Unknown"
    recent_high: float | None = None
    recent_low: float | None = None
    swing_highs: list[float] = Field(default_factory=list)
    swing_lows: list[float] = Field(default_factory=list)
    candle_closes: list[float] = Field(default_factory=list)
    candle_count: int = 0
    image_quality: float = 0.0
    captured_at: datetime | None = None


class MarketPayload(BaseModel):
    pair: str
    timeframe: str
    candles: list[OHLCCandle] = Field(default_factory=list)
    as_of: datetime | None = None
    provider_name: str = "request"


class VerifyRequest(BaseModel):
    """
    Optional verification request.

    Omit `market` to simulate screenshot-only / missing provider.
    """

    visual: VisualPayload
    market: MarketPayload | None = None
    persist: bool = False


@router.post("/verification/check")
def verification_check(body: VerifyRequest) -> dict:
    """
    Compare a screenshot-derived visual snapshot with optional OHLC market data.

    Never fails the analysis path — returns screenshot_only / unavailable statuses
    when market data is missing.
    """
    visual = ChartVisualSnapshot(**body.visual.model_dump())
    market: MarketDataSnapshot | None = None
    if body.market is not None:
        market = MarketDataSnapshot(**body.market.model_dump())

    engine = VerificationEngine(provider=NullMarketDataProvider(), reporter=_reporter)
    summary = engine.verify(visual, market, persist=body.persist)
    return {"verification": summary.model_dump(mode="json")}


@router.get("/verification/discrepancies")
def list_discrepancies(limit: int = 50) -> dict:
    """List recently stored verification discrepancies for review."""
    return {"items": _reporter.list_recent(limit=limit)}


@router.get("/verification/health")
def verification_health() -> dict:
    """Provider-agnostic health — default Null provider is always screenshot-safe."""
    null = NullMarketDataProvider()
    return {
        "default_provider": null.name,
        "available": null.available(),
        "screenshot_only_supported": True,
        "pluggable": True,
        "note": "Inject InMemoryMarketDataProvider or a live vendor adapter via AIBrain(market_provider=...).",
        "example_provider": InMemoryMarketDataProvider.__name__,
    }
