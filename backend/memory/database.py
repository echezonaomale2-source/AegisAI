"""SQLite memory database — permanent trade experience store."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from config.settings import settings

_DB_PATH = settings.upload_dir.parent / "storage" / "aegis_memory.db"


SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;

CREATE TABLE IF NOT EXISTS memories (
    trade_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    pair TEXT NOT NULL,
    timeframes_json TEXT NOT NULL,
    chart_4h_path TEXT,
    chart_1h_path TEXT,
    chart_15m_path TEXT,
    features_json TEXT NOT NULL,
    analysis_4h_json TEXT NOT NULL,
    analysis_1h_json TEXT NOT NULL,
    analysis_15m_json TEXT NOT NULL,
    final_decision TEXT NOT NULL,
    entry TEXT,
    stop_loss TEXT,
    take_profit TEXT,
    risk_reward TEXT,
    confidence REAL NOT NULL,
    explanation TEXT,
    status TEXT NOT NULL,
    outcome TEXT,
    outcome_chart_path TEXT,
    lesson TEXT,
    fingerprint_bits TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    direction TEXT NOT NULL,
    closed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_memories_pair ON memories(pair);
CREATE INDEX IF NOT EXISTS idx_memories_outcome ON memories(outcome);
CREATE INDEX IF NOT EXISTS idx_memories_direction ON memories(direction);
CREATE INDEX IF NOT EXISTS idx_memories_fp_hash ON memories(fingerprint_hash);
CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status);
CREATE INDEX IF NOT EXISTS idx_memories_closed ON memories(closed_at);
CREATE INDEX IF NOT EXISTS idx_memories_timestamp ON memories(timestamp DESC);

CREATE TABLE IF NOT EXISTS feature_stats (
    feature_key TEXT PRIMARY KEY,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS learning_weights (
    weight_key TEXT PRIMARY KEY,
    weight_value REAL NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS learning_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patterns (
    pattern_key TEXT PRIMARY KEY,
    pattern_label TEXT NOT NULL,
    features_json TEXT NOT NULL,
    trades INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    rr_sum REAL NOT NULL DEFAULT 0,
    confidence_sum REAL NOT NULL DEFAULT 0,
    last_updated TEXT
);

CREATE INDEX IF NOT EXISTS idx_patterns_wins ON patterns(wins DESC);

CREATE TABLE IF NOT EXISTS reviews (
    trade_id TEXT PRIMARY KEY,
    grade TEXT NOT NULL,
    scorecard_json TEXT NOT NULL,
    critique_json TEXT NOT NULL,
    questions_json TEXT NOT NULL,
    lessons_json TEXT NOT NULL,
    summary TEXT,
    outcome_analysis_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(trade_id) REFERENCES memories(trade_id)
);
"""


def get_db_path() -> Path:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return _DB_PATH


def connect() -> sqlite3.Connection:
    path = get_db_path()
    # Integrity check before open for writes — quarantine corrupt DBs.
    if path.exists() and path.stat().st_size > 0:
        try:
            probe = sqlite3.connect(str(path))
            row = probe.execute("PRAGMA integrity_check").fetchone()
            ok = row and str(row[0]).lower() == "ok"
            probe.close()
            if not ok:
                corrupt = path.with_suffix(path.suffix + ".corrupt")
                path.replace(corrupt)
        except sqlite3.Error:
            corrupt = path.with_suffix(path.suffix + ".corrupt")
            try:
                path.replace(corrupt)
            except OSError:
                pass
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Additive migrations for Phase 4.5 columns on existing DBs."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(memories)").fetchall()}
    alterations = {
        "grade": "ALTER TABLE memories ADD COLUMN grade TEXT",
        "review_json": "ALTER TABLE memories ADD COLUMN review_json TEXT",
        "lessons_json": "ALTER TABLE memories ADD COLUMN lessons_json TEXT",
        "pattern_key": "ALTER TABLE memories ADD COLUMN pattern_key TEXT",
    }
    for name, sql in alterations.items():
        if name not in cols:
            conn.execute(sql)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_grade ON memories(grade)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_pattern ON memories(pattern_key)"
    )


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        # Seed baseline weights if empty.
        from decision.confidence_engine import WEIGHTS

        for key, value in WEIGHTS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO learning_weights (weight_key, weight_value, sample_count, last_updated)
                VALUES (?, ?, 0, NULL)
                """,
                (key, value),
            )
        conn.execute(
            """
            INSERT OR IGNORE INTO learning_meta (meta_key, meta_value)
            VALUES ('last_learning_update', 'never')
            """
        )
        conn.commit()


# Initialize on import.
init_db()
