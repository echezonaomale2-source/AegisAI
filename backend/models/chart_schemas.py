"""Phase 2 chart analysis schemas — structured SMC extraction (no trade bias)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TrendLabel = Literal["Bullish", "Bearish", "Range", "Unknown"]
PremiumDiscountYesNo = Literal["Yes", "No", "Unknown"]


class ConfidenceBreakdown(BaseModel):
    trend: float = Field(ge=0, le=100)
    market_structure: float = Field(ge=0, le=100)
    bos: float = Field(ge=0, le=100)
    choch: float = Field(ge=0, le=100)
    liquidity: float = Field(ge=0, le=100)
    liquidity_sweep: float = Field(ge=0, le=100)
    order_block: float = Field(ge=0, le=100)
    fair_value_gap: float = Field(ge=0, le=100)
    zones: float = Field(ge=0, le=100)
    overall: float = Field(ge=0, le=100)


class PriceContext(BaseModel):
    """Chart-relative price geometry (0–100 scale from vision pipeline)."""

    last_close: float | None = None
    last_high: float | None = None
    last_low: float | None = None
    swing_high: float | None = None
    swing_low: float | None = None
    range_high: float | None = None
    range_low: float | None = None
    avg_range: float | None = None


class ChartAnalysis(BaseModel):
    """Single-chart Smart Money Concepts extraction result."""

    status: Literal["ok", "error"] = "ok"
    error: str | None = None
    pair: str = "Unknown"
    timeframe: str = "Unknown"
    detected_timeframe_label: str | None = None
    trend: TrendLabel = "Unknown"
    market_structure: str = "Unknown"
    bos: bool = False
    choch: bool = False
    liquidity: str = "None Detected"
    liquidity_sweep: bool = False
    equal_highs: bool = False
    equal_lows: bool = False
    internal_liquidity: bool = False
    external_liquidity: bool = False
    bullish_order_block: bool = False
    bearish_order_block: bool = False
    fair_value_gap: bool = False
    fvg_type: str | None = None
    supply_zone: bool = False
    demand_zone: bool = False
    premium: PremiumDiscountYesNo = "Unknown"
    discount: PremiumDiscountYesNo = "Unknown"
    strong_rejection: bool = False
    weak_rejection: bool = False
    impulse_move: bool = False
    correction_move: bool = False
    session_labels: list[str] = Field(default_factory=list)
    candle_count: int = 0
    swing_high_count: int = 0
    swing_low_count: int = 0
    price_context: PriceContext | None = None
    confidence: float = Field(default=0, ge=0, le=100)
    confidence_breakdown: ConfidenceBreakdown | None = None
    notes: list[str] = Field(default_factory=list)


class MultiChartAnalysis(BaseModel):
    """Independent analyses for 4H / 1H / 15M — not combined."""

    status: Literal["ok", "partial", "error"] = "ok"
    chart_4h: ChartAnalysis
    chart_1h: ChartAnalysis
    chart_15m: ChartAnalysis
    notes: list[str] = Field(default_factory=list)
