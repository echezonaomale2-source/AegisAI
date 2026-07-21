import type { AnalysisResult, TradeOutcome, TradeRecord } from '../types/analysis';
import { decryptText, encryptText, isEncrypted } from './crypto';
import { getDatabase } from './database';

interface TradeRow {
  id: string;
  created_at: string;
  updated_at: string;
  pair: string;
  bias: string;
  confidence: number;
  entry: string;
  stop_loss: string;
  take_profit: string;
  risk_reward: string;
  chart_4h_uri: string;
  chart_1h_uri: string;
  chart_15m_uri: string;
  outcome_chart_uri: string | null;
  outcome: string | null;
  analysis_json: string;
  final_decision: string;
  status: string;
  comments?: string | null;
  rr_achieved?: string | null;
  sync_status?: string | null;
  analysis_encrypted?: number | null;
}

async function mapRow(row: TradeRow): Promise<TradeRecord> {
  let analysisJson = row.analysis_json;
  if (isEncrypted(analysisJson) || row.analysis_encrypted === 1) {
    analysisJson = await decryptText(analysisJson);
  }
  return {
    id: row.id,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
    pair: row.pair,
    bias: row.bias as TradeRecord['bias'],
    confidence: row.confidence,
    entry: row.entry,
    stopLoss: row.stop_loss,
    takeProfit: row.take_profit,
    riskReward: row.risk_reward,
    chart4hUri: row.chart_4h_uri,
    chart1hUri: row.chart_1h_uri,
    chart15mUri: row.chart_15m_uri,
    outcomeChartUri: row.outcome_chart_uri,
    outcome: row.outcome as TradeOutcome,
    analysisJson,
    finalDecision: row.final_decision,
    status: row.status as TradeRecord['status'],
    comments: row.comments ?? null,
    rrAchieved: row.rr_achieved ?? null,
    syncStatus: (row.sync_status as TradeRecord['syncStatus']) ?? 'synced',
  };
}

export async function insertTrade(trade: TradeRecord): Promise<void> {
  const db = await getDatabase();
  const encryptedAnalysis = await encryptText(trade.analysisJson);
  await db.runAsync(
    `INSERT INTO trades (
      id, created_at, updated_at, pair, bias, confidence,
      entry, stop_loss, take_profit, risk_reward,
      chart_4h_uri, chart_1h_uri, chart_15m_uri,
      outcome_chart_uri, outcome, analysis_json, final_decision, status,
      comments, rr_achieved, sync_status, analysis_encrypted
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
    [
      trade.id,
      trade.createdAt,
      trade.updatedAt,
      trade.pair,
      trade.bias,
      trade.confidence,
      trade.entry,
      trade.stopLoss,
      trade.takeProfit,
      trade.riskReward,
      trade.chart4hUri,
      trade.chart1hUri,
      trade.chart15mUri,
      trade.outcomeChartUri,
      trade.outcome,
      encryptedAnalysis,
      trade.finalDecision,
      trade.status,
      trade.comments ?? null,
      trade.rrAchieved ?? null,
      trade.syncStatus ?? 'synced',
      1,
    ],
  );
}

export async function getAllTrades(): Promise<TradeRecord[]> {
  const db = await getDatabase();
  const rows = await db.getAllAsync<TradeRow>(
    'SELECT * FROM trades ORDER BY created_at DESC',
  );
  return Promise.all(rows.map(mapRow));
}

export async function getTradeById(id: string): Promise<TradeRecord | null> {
  const db = await getDatabase();
  const row = await db.getFirstAsync<TradeRow>('SELECT * FROM trades WHERE id = ?', [id]);
  return row ? mapRow(row) : null;
}

export async function updateTradeOutcome(
  id: string,
  outcome: Exclude<TradeOutcome, null>,
  outcomeChartUri: string,
  extras?: { comments?: string; rrAchieved?: string; syncStatus?: TradeRecord['syncStatus'] },
): Promise<void> {
  const db = await getDatabase();
  const updatedAt = new Date().toISOString();
  await db.runAsync(
    `UPDATE trades
     SET outcome = ?, outcome_chart_uri = ?, status = 'CLOSED', updated_at = ?,
         comments = COALESCE(?, comments),
         rr_achieved = COALESCE(?, rr_achieved),
         sync_status = COALESCE(?, sync_status)
     WHERE id = ?`,
    [
      outcome,
      outcomeChartUri,
      updatedAt,
      extras?.comments ?? null,
      extras?.rrAchieved ?? null,
      extras?.syncStatus ?? null,
      id,
    ],
  );
}

export function parseAnalysis(trade: TradeRecord): AnalysisResult {
  return JSON.parse(trade.analysisJson) as AnalysisResult;
}
