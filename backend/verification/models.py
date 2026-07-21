"""
Market data verification models (Phase 11).

Screenshot analysis remains primary. OHLC market data is optional verification.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


DiscrepancyKind = Literal[
    "timeframe_mismatch",
    "pair_mismatch",
    "trend_mismatch",
    "swing_structure_mismatch",
    "high_mismatch",
    "low_mismatch",
    "candle_sequence_mismatch",
    "missing_candles",
    "image_too_old",
    "unable_to_verify",
]

VerificationStatus = Literal[
    "screenshot_only",
    "verified_match",
    "verified_partial",
    "verified_conflict",
    "unavailable",
    "error",
]

DiscrepancySeverity = Literal["none", "low", "medium", "high"]


class OHLCCandle(BaseModel):
    """Vendor-agnostic OHLC bar."""

    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    timestamp: datetime | None = None
    index: int | None = None


class MarketDataSnapshot(BaseModel):
    """
    Optional market-data payload from any pluggable provider.

    Never required to complete an analysis.
    """

    pair: str
    timeframe: str
    candles: list[OHLCCandle] = Field(default_factory=list)
    as_of: datetime | None = None
    provider_name: str = "unknown"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return len(self.candles) >= 3


class ChartVisualSnapshot(BaseModel):
    """
    Screenshot-derived view used for comparison.

    Built from Vision / MarketModel — never from broker OHLC.
    """

    pair: str = "Unknown"
    timeframe: str = "Unknown"
    trend: str = "Unknown"
    structure_label: str = "Unknown"
    recent_high: float | None = None
    recent_low: float | None = None
    swing_highs: list[float] = Field(default_factory=list)
    swing_lows: list[float] = Field(default_factory=list)
    candle_closes: list[float] = Field(default_factory=list)
    candle_count: int = 0
    image_quality: float = Field(default=0.0, ge=0, le=100)
    captured_at: datetime | None = None
    source: str = "screenshot"


class Discrepancy(BaseModel):
    kind: DiscrepancyKind
    severity: DiscrepancySeverity = "medium"
    message: str
    screenshot_value: str | None = None
    market_value: str | None = None
    detail: dict[str, Any] = Field(default_factory=dict)


class VerificationSummary(BaseModel):
    """
    Result of optional market-data verification.

    influence_on_confidence: signed delta applied by the Brain.
    Verification strengthens or weakens confidence — never replaces visual bias.
    """

    status: VerificationStatus = "screenshot_only"
    provider_used: str | None = None
    pair: str = "Unknown"
    timeframe: str = "Unknown"
    discrepancies: list[Discrepancy] = Field(default_factory=list)
    match_score: float = Field(default=0.0, ge=0, le=100)
    influence_on_confidence: float = 0.0
    significant_disagreement: bool = False
    screenshot_only: bool = True
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    verified_at: datetime | None = None

    @property
    def has_discrepancies(self) -> bool:
        return len(self.discrepancies) > 0
