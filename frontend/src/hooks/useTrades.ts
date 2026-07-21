import { useCallback, useEffect, useState } from 'react';
import type { TradeRecord } from '../types/analysis';
import { getAllTrades, getTradeById } from '../storage/tradeRepository';

export function useTrades() {
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const records = await getAllTrades();
      setTrades(records);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { trades, loading, refresh };
}

export function useTrade(tradeId: string) {
  const [trade, setTrade] = useState<TradeRecord | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const record = await getTradeById(tradeId);
      setTrade(record);
    } finally {
      setLoading(false);
    }
  }, [tradeId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { trade, loading, refresh };
}
