import { createId } from '../utils/formatters';
import { getDatabase } from './database';
import { submitTradeOutcome } from '../services/api';

export interface OutcomeSyncPayload {
  tradeId: string;
  outcome: 'TAKE_PROFIT' | 'STOP_LOSS' | 'BREAK_EVEN';
  resultChartUri: string;
  comments?: string;
  rrAchieved?: string;
}

interface SyncRow {
  id: string;
  trade_id: string;
  kind: string;
  payload_json: string;
  attempts: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

export async function enqueueOutcomeSync(payload: OutcomeSyncPayload): Promise<string> {
  const db = await getDatabase();
  const id = createId();
  const now = new Date().toISOString();
  await db.runAsync(
    `INSERT INTO sync_queue (id, trade_id, kind, payload_json, attempts, last_error, created_at, updated_at)
     VALUES (?, ?, 'outcome', ?, 0, NULL, ?, ?)`,
    [id, payload.tradeId, JSON.stringify(payload), now, now],
  );
  return id;
}

export async function flushOutcomeSyncQueue(): Promise<{ flushed: number; failed: number }> {
  const db = await getDatabase();
  const rows = await db.getAllAsync<SyncRow>(
    `SELECT * FROM sync_queue WHERE kind = 'outcome' ORDER BY created_at ASC LIMIT 20`,
  );
  let flushed = 0;
  let failed = 0;

  for (const row of rows) {
    const payload = JSON.parse(row.payload_json) as OutcomeSyncPayload;
    try {
      await submitTradeOutcome({
        tradeId: payload.tradeId,
        outcome: payload.outcome === 'BREAK_EVEN' ? 'BREAK_EVEN' : payload.outcome,
        resultChartUri: payload.resultChartUri,
        comments: payload.comments,
        rrAchieved: payload.rrAchieved,
      });
      await db.runAsync('DELETE FROM sync_queue WHERE id = ?', [row.id]);
      await db.runAsync(
        `UPDATE trades SET sync_status = 'synced', updated_at = ? WHERE id = ?`,
        [new Date().toISOString(), payload.tradeId],
      );
      flushed += 1;
    } catch (error) {
      failed += 1;
      const message = error instanceof Error ? error.message : 'sync failed';
      await db.runAsync(
        `UPDATE sync_queue SET attempts = attempts + 1, last_error = ?, updated_at = ? WHERE id = ?`,
        [message, new Date().toISOString(), row.id],
      );
      await db.runAsync(
        `UPDATE trades SET sync_status = 'error', updated_at = ? WHERE id = ?`,
        [new Date().toISOString(), payload.tradeId],
      );
    }
  }

  return { flushed, failed };
}

export async function pendingSyncCount(): Promise<number> {
  const db = await getDatabase();
  const row = await db.getFirstAsync<{ c: number }>(
    `SELECT COUNT(*) as c FROM sync_queue WHERE kind = 'outcome'`,
  );
  return row?.c ?? 0;
}
