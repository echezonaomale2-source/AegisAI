from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TradeBias = Literal["BUY", "SELL", "NO TRADE"]
TrendBias = Literal["Bullish", "Bearish", "Consolidation"]
MarketStructureLabel = Literal[
    "Higher High",
    "Lower Low",
    "Higher Low",
    "Lower High",
    "Break Of Structure",
    "Change Of Character",
    "Neutral",
]
LiquidityLabel = Literal[
    "Liquidity Sweep",
    "Equal Highs",
    "Equal Lows",
    "Buy Side Liquidity",
    "Sell Side Liquidity",
    "None Detected",
]
OrderBlockLabel = Literal[
    "Bullish Order Block",
    "Bearish Order Block",
    "Mitigated",
    "None Detected",
]
FvgLabel = Literal["Bullish FVG", "Bearish FVG", "Filled", "None Detected"]
PremiumDiscount = Literal["Premium", "Discount", "Equilibrium"]
SupplyDemand = Literal["Supply", "Demand", "Balanced"]


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class TimeframeAnalysis4H(CamelModel):
    trend: TrendBias
    marketStructure: MarketStructureLabel
    liquidity: LiquidityLabel
    orderBlock: OrderBlockLabel
    fvg: FvgLabel
    premiumDiscount: PremiumDiscount
    supplyDemand: SupplyDemand
    summary: str


class TimeframeAnalysis1H(CamelModel):
    trend: TrendBias
    liquidity: LiquidityLabel
    orderBlock: OrderBlockLabel
    fvg: FvgLabel
    summary: str


class TimeframeAnalysis15M(CamelModel):
    entry: str
    stopLoss: str
    takeProfit: str
    riskReward: str
    reasons: list[str]
    summary: str


class AnalysisResult(CamelModel):
    pair: str
    bias: TradeBias
    confidence: float = Field(ge=0, le=100)
    analysis4h: TimeframeAnalysis4H
    analysis1h: TimeframeAnalysis1H
    analysis15m: TimeframeAnalysis15M
    finalDecision: str
    generatedAt: str
    warnings: list[str] = Field(default_factory=list)
    explanation: str | None = None
    targetLiquidity: str | None = None
    tradeId: str | None = None
    status: str | None = "Waiting Result"


class HealthResponse(CamelModel):
    status: str
    service: str
    version: str
    timestamp: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
