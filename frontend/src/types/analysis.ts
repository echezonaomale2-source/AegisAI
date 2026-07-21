export type TradeBias = 'BUY' | 'SELL' | 'NO TRADE';

export type TrendBias = 'Bullish' | 'Bearish' | 'Consolidation';

export type MarketStructureLabel =
  | 'Higher High'
  | 'Lower Low'
  | 'Higher Low'
  | 'Lower High'
  | 'Break Of Structure'
  | 'Change Of Character'
  | 'Neutral';

export type LiquidityLabel =
  | 'Liquidity Sweep'
  | 'Equal Highs'
  | 'Equal Lows'
  | 'Buy Side Liquidity'
  | 'Sell Side Liquidity'
  | 'None Detected';

export type OrderBlockLabel =
  | 'Bullish Order Block'
  | 'Bearish Order Block'
  | 'Mitigated'
  | 'None Detected';

export type FvgLabel =
  | 'Bullish FVG'
  | 'Bearish FVG'
  | 'Filled'
  | 'None Detected';

export type PremiumDiscount = 'Premium' | 'Discount' | 'Equilibrium';

export type SupplyDemand = 'Supply' | 'Demand' | 'Balanced';

export interface TimeframeAnalysis4H {
  trend: TrendBias;
  marketStructure: MarketStructureLabel;
  liquidity: LiquidityLabel;
  orderBlock: OrderBlockLabel;
  fvg: FvgLabel;
  premiumDiscount: PremiumDiscount;
  supplyDemand: SupplyDemand;
  summary: string;
}

export interface TimeframeAnalysis1H {
  trend: TrendBias;
  liquidity: LiquidityLabel;
  orderBlock: OrderBlockLabel;
  fvg: FvgLabel;
  summary: string;
}

export interface TimeframeAnalysis15M {
  entry: string;
  stopLoss: string;
  takeProfit: string;
  riskReward: string;
  reasons: string[];
  summary: string;
}

export interface AnalysisResult {
  pair: string;
  bias: TradeBias;
  confidence: number;
  timeframes?: {
    HTF?: string;
    MTF?: string;
    LTF?: string;
    [key: string]: string | undefined;
  };
  analysis4h: TimeframeAnalysis4H;
  analysis1h: TimeframeAnalysis1H;
  analysis15m: TimeframeAnalysis15M;
  finalDecision: string;
  generatedAt: string;
  warnings?: string[];
  explanation?: string;
  targetLiquidity?: string;
  tradeId?: string;
  status?: string;
}

export type TradeOutcome = 'TAKE_PROFIT' | 'STOP_LOSS' | 'BREAK_EVEN' | null;

export interface TradeRecord {
  id: string;
  createdAt: string;
  updatedAt: string;
  pair: string;
  bias: TradeBias;
  confidence: number;
  entry: string;
  stopLoss: string;
  takeProfit: string;
  riskReward: string;
  chart4hUri: string;
  chart1hUri: string;
  chart15mUri: string;
  outcomeChartUri: string | null;
  outcome: TradeOutcome;
  analysisJson: string;
  finalDecision: string;
  status: 'WAITING' | 'CLOSED';
  comments?: string | null;
  rrAchieved?: string | null;
  syncStatus?: 'synced' | 'pending' | 'error';
}

export interface ChartUploads {
  chart4h: string | null;
  chart1h: string | null;
  chart15m: string | null;
}
