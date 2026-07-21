"""Phase 11 — optional market data verification layer."""

from __future__ import annotations

from verification.discrepancy import DiscrepancyReporter
from verification.engine import VerificationEngine
from verification.models import (
    ChartVisualSnapshot,
    Discrepancy,
    MarketDataSnapshot,
    OHLCCandle,
    VerificationSummary,
)
from verification.provider import (
    InMemoryMarketDataProvider,
    MarketDataProvider,
    NullMarketDataProvider,
    make_ohlc_series,
)

__all__ = [
    "ChartVisualSnapshot",
    "Discrepancy",
    "DiscrepancyReporter",
    "InMemoryMarketDataProvider",
    "MarketDataProvider",
    "MarketDataSnapshot",
    "NullMarketDataProvider",
    "OHLCCandle",
    "VerificationEngine",
    "VerificationSummary",
    "make_ohlc_series",
]
