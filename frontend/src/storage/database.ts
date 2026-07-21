import * as SQLite from 'expo-sqlite';

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

async function migrate(db: SQLite.SQLiteDatabase): Promise<void> {
  const cols = await db.getAllAsync<{ name: string }>('PRAGMA table_info(trades)');
  const names = new Set(cols.map((c) => c.name));

  if (!names.has('comments')) {
    await db.execAsync('ALTER TABLE trades ADD COLUMN comments TEXT');
  }
  if (!names.has('rr_achieved')) {
    await db.execAsync('ALTER TABLE trades ADD COLUMN rr_achieved TEXT');
  }
  if (!names.has('sync_status')) {
    await db.execAsync(
      "ALTER TABLE trades ADD COLUMN sync_status TEXT NOT NULL DEFAULT 'synced'",
    );
  }
  if (!names.has('analysis_encrypted')) {
    await db.execAsync(
      'ALTER TABLE trades ADD COLUMN analysis_encrypted INTEGER NOT NULL DEFAULT 0',
    );
  }

  await db.execAsync(`
    CREATE TABLE IF NOT EXISTS sync_queue (
      id TEXT PRIMARY KEY NOT NULL,
      trade_id TEXT NOT NULL,
      kind TEXT NOT NULL,
      payload_json TEXT NOT NULL,
      attempts INTEGER NOT NULL DEFAULT 0,
      last_error TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_sync_queue_created ON sync_queue(created_at ASC);
  `);
}

export async function getDatabase(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync('aegisai.db');
      await db.execAsync(`
        PRAGMA journal_mode = WAL;
        PRAGMA foreign_keys = ON;

        CREATE TABLE IF NOT EXISTS trades (
          id TEXT PRIMARY KEY NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          pair TEXT NOT NULL,
          bias TEXT NOT NULL,
          confidence REAL NOT NULL,
          entry TEXT NOT NULL,
          stop_loss TEXT NOT NULL,
          take_profit TEXT NOT NULL,
          risk_reward TEXT NOT NULL,
          chart_4h_uri TEXT NOT NULL,
          chart_1h_uri TEXT NOT NULL,
          chart_15m_uri TEXT NOT NULL,
          outcome_chart_uri TEXT,
          outcome TEXT,
          analysis_json TEXT NOT NULL,
          final_decision TEXT NOT NULL,
          status TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_trades_created_at ON trades(created_at DESC);
      `);
      await migrate(db);
      return db;
    })();
  }

  return dbPromise;
}

/** Test helper — reset singleton between suites if needed. */
export function resetDatabaseSingleton(): void {
  dbPromise = null;
}
