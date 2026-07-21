"""
Chart reconstruction models.

ChartModel is the canonical internal representation of a trading chart.
After reconstruction, no module may access raw images — only ChartModel.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TrendDirection = Literal["Bullish", "Bearish", "Range", "Unknown"]
ZoneSide = Literal["Bullish", "Bearish", "Neutral", "Unknown"]


class Candle(BaseModel):
    """Reconstructed OHLC candle (chart-relative coordinates)."""

    index: int
    open: float
    high: float
    low: float
    close: float
    bullish: bool
    body_size: float
    upper_wick: float
    lower_wick: float
    relative_position: float = Field(ge=0, le=1, default=0.0)
    confidence: float = Field(ge=0, le=100, default=70.0)


class SwingPoint(BaseModel):
    index: int
    price: float
    kind: Literal["high", "low"]
    structure_label: str | None = None  # HH / HL / LH / LL
    confidence: float = Field(ge=0, le=100, default=0.0)


class Trend(BaseModel):
    direction: TrendDirection = "Unknown"
    confidence: float = Field(ge=0, le=100, default=0.0)
    impulse_move: bool = False
    pullback: bool = False
    notes: list[str] = Field(default_factory=list)


class LiquidityZone(BaseModel):
    id: str
    kind: Literal[
        "equal_highs",
        "equal_lows",
        "buy_side",
        "sell_side",
        "sweep",
        "internal",
        "external",
        "unknown",
    ] = "unknown"
    price: float | None = None
    swept: bool = False
    confidence: float = Field(ge=0, le=100, default=0.0)
    supporting_candles: list[int] = Field(default_factory=list)
    label: str | None = None


class OrderBlock(BaseModel):
    id: str
    side: Literal["bullish", "bearish", "unknown"] = "unknown"
    high: float | None = None
    low: float | None = None
    mitigated: bool = False
    confidence: float = Field(ge=0, le=100, default=0.0)
    supporting_candles: list[int] = Field(default_factory=list)


class FairValueGap(BaseModel):
    id: str
    side: Literal["bullish", "bearish", "unknown"] = "unknown"
    high: float | None = None
    low: float | None = None
    filled: bool = False
    confidence: float = Field(ge=0, le=100, default=0.0)
    supporting_candles: list[int] = Field(default_factory=list)


class SupplyZone(BaseModel):
    id: str
    high: float | None = None
    low: float | None = None
    confidence: float = Field(ge=0, le=100, default=0.0)
    supporting_candles: list[int] = Field(default_factory=list)


class DemandZone(BaseModel):
    id: str
    high: float | None = None
    low: float | None = None
    confidence: float = Field(ge=0, le=100, default=0.0)
    supporting_candles: list[int] = Field(default_factory=list)


class ChartModel(BaseModel):
    """
    Fully reconstructed chart — the only input for SMC / decision / learning.

    Contains no image buffers or pixel data.
    """

    status: Literal["ok", "error", "unknown"] = "ok"
    error: str | None = None
    pair: str = "Unknown"
    timeframe: str = "Unknown"
    detected_timeframe_label: str | None = None
    price_scale: dict[str, Any] | None = None
    chart_bounds: dict[str, int] | None = None
    session_labels: list[str] = Field(default_factory=list)
    image_quality_score: float = Field(ge=0, le=100, default=0.0)
    pair_confidence: float = Field(ge=0, le=100, default=0.0)
    timeframe_confidence: float = Field(ge=0, le=100, default=0.0)

    candles: list[Candle] = Field(default_factory=list)
    swing_points: list[SwingPoint] = Field(default_factory=list)
    trend: Trend = Field(default_factory=Trend)
    market_structure_label: str = "Unknown"
    bos: bool = False
    choch: bool = False
    liquidity_zones: list[LiquidityZone] = Field(default_factory=list)
    order_blocks: list[OrderBlock] = Field(default_factory=list)
    fair_value_gaps: list[FairValueGap] = Field(default_factory=list)
    supply_zones: list[SupplyZone] = Field(default_factory=list)
    demand_zones: list[DemandZone] = Field(default_factory=list)
    premium: Literal["Yes", "No", "Unknown"] = "Unknown"
    discount: Literal["Yes", "No", "Unknown"] = "Unknown"
    strong_rejection: bool = False
    weak_rejection: bool = False

    source_image_path: str | None = Field(
        default=None,
        description="Path reference for memory only — never used for reasoning",
    )
    reconstruction_confidence: float = Field(ge=0, le=100, default=0.0)
    notes: list[str] = Field(default_factory=list)
    cache_hit: bool = False

    @property
    def is_usable(self) -> bool:
        return self.status == "ok" and len(self.candles) >= 5
