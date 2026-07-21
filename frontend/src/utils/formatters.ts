import type { TradeBias, TradeOutcome } from '../types/analysis';
import { colors } from '../theme/colors';

export function formatTimestamp(iso: string): string {
  const date = new Date(iso);
  return date.toLocaleString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export function formatConfidence(value: number): string {
  return `${Math.round(value)}%`;
}

export function biasColor(bias: TradeBias): string {
  switch (bias) {
    case 'BUY':
      return colors.buy;
    case 'SELL':
      return colors.sell;
    default:
      return colors.noTrade;
  }
}

export function outcomeLabel(outcome: TradeOutcome): string {
  if (outcome === 'TAKE_PROFIT') return 'Take Profit';
  if (outcome === 'STOP_LOSS') return 'Stop Loss';
  if (outcome === 'BREAK_EVEN') return 'Break Even';
  return 'Waiting Result';
}

export function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}
