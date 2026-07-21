"""
Research SQLite schema — additive tables for calibration, patterns, lessons, cache.

Uses the same DB file as memory for join convenience; never alters legacy table shapes
except additive CREATE TABLE / INDEX.
"""

from __future__ import annotations

from memory.database import connect, init_db as _ensure_memory_db

RESEARCH_SCHEMA = """
CREATE TABLE IF NOT EXISTS research_calibration_bins (
    bin_label TEXT PRIMARY KEY,
    min_confidence REAL NOT NULL,
    max_confidence REAL NOT NULL,
    predictions INTEGER NOT NULL DEFAULT 0,
    successes INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS research_calibration_meta (
    meta_key TEXT PRIMARY KEY,
    meta_value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS research_patterns (
    pattern_id TEXT PRIMARY KEY,
    features_json TEXT NOT NULL,
    occurrences INTEGER NOT NULL DEFAULT 0,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    no_trade_recommendations INTEGER NOT NULL DEFAULT 0,
    confidence_sum REAL NOT NULL DEFAULT 0,
    rr_sum REAL NOT NULL DEFAULT 0,
    holding_hours_sum REAL NOT NULL DEFAULT 0,
    holding_samples INTEGER NOT NULL DEFAULT 0,
    last_updated TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_patterns_occ ON research_patterns(occurrences DESC);
CREATE INDEX IF NOT EXISTS idx_research_patterns_wins ON research_patterns(wins DESC);
CREATE INDEX IF NOT EXISTS idx_research_patterns_losses ON research_patterns(losses DESC);

CREATE TABLE IF NOT EXISTS research_reviews (
    trade_id TEXT PRIMARY KEY,
    outcome TEXT NOT NULL,
    decision_quality TEXT NOT NULL,
    scorecard_json TEXT NOT NULL,
    report_json TEXT NOT NULL,
    cognitive_hash TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_reviews_quality ON research_reviews(decision_quality);
CREATE INDEX IF NOT EXISTS idx_research_reviews_created ON research_reviews(created_at DESC);

CREATE TABLE IF NOT EXISTS research_lessons (
    lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id TEXT,
    lesson_text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_lessons_created ON research_lessons(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_research_lessons_trade ON research_lessons(trade_id);

CREATE TABLE IF NOT EXISTS research_no_trade_reasons (
    reason_key TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_no_trade_count ON research_no_trade_reasons(count DESC);

CREATE TABLE IF NOT EXISTS research_loss_reasons (
    reason_key TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 0,
    last_seen TEXT
);

CREATE INDEX IF NOT EXISTS idx_research_loss_count ON research_loss_reasons(count DESC);

CREATE TABLE IF NOT EXISTS research_analysis_cache (
    cache_key TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    last_accessed TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_research_cache_hash ON research_analysis_cache(content_hash);
CREATE INDEX IF NOT EXISTS idx_research_cache_accessed ON research_analysis_cache(last_accessed);

-- Extra memory indexes for 100k-scale research queries (idempotent).
CREATE INDEX IF NOT EXISTS idx_memories_confidence ON memories(confidence);
CREATE INDEX IF NOT EXISTS idx_memories_decision_conf ON memories(final_decision, confidence);
CREATE INDEX IF NOT EXISTS idx_memories_outcome_conf ON memories(outcome, confidence);
"""

_CALIBRATION_BINS = [
    ("0-50", 0.0, 50.0),
    ("50-60", 50.0, 60.0),
    ("60-70", 60.0, 70.0),
    ("70-80", 70.0, 80.0),
    ("80-90", 80.0, 90.0),
    ("90-100", 90.0, 100.01),
]


def init_research_db() -> None:
    _ensure_memory_db()
    with connect() as conn:
        conn.executescript(RESEARCH_SCHEMA)
        for label, lo, hi in _CALIBRATION_BINS:
            conn.execute(
                """
                INSERT OR IGNORE INTO research_calibration_bins
                (bin_label, min_confidence, max_confidence, predictions, successes, last_updated)
                VALUES (?, ?, ?, 0, 0, NULL)
                """,
                (label, lo, hi),
            )
        conn.execute(
            """
            INSERT OR IGNORE INTO research_calibration_meta (meta_key, meta_value)
            VALUES ('adjustment_factor', '1.0')
            """
        )
        conn.execute(
            """
            INSERT OR IGNORE INTO research_calibration_meta (meta_key, meta_value)
            VALUES ('sample_count', '0')
            """
        )
        conn.commit()


# Initialize on import.
init_research_db()
