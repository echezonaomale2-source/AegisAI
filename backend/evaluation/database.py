"""Evaluation SQLite schema — logs, reports, A/B tests, counters."""

from __future__ import annotations

from memory.database import connect, init_db as _ensure_memory_db

EVAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS eval_decision_paths (
    log_id TEXT PRIMARY KEY,
    trade_id TEXT,
    timestamp TEXT NOT NULL,
    decision TEXT NOT NULL,
    confidence REAL NOT NULL,
    knowledge_version TEXT,
    variant_id TEXT,
    payload_json TEXT NOT NULL,
    outcome TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_paths_trade ON eval_decision_paths(trade_id);
CREATE INDEX IF NOT EXISTS idx_eval_paths_ts ON eval_decision_paths(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_eval_paths_decision ON eval_decision_paths(decision);
CREATE INDEX IF NOT EXISTS idx_eval_paths_variant ON eval_decision_paths(variant_id);

CREATE TABLE IF NOT EXISTS eval_counters (
    counter_key TEXT PRIMARY KEY,
    counter_value REAL NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS eval_feature_events (
    feature_key TEXT PRIMARY KEY,
    detections INTEGER NOT NULL DEFAULT 0,
    unknowns INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_eval_feature_det ON eval_feature_events(detections DESC);

CREATE TABLE IF NOT EXISTS eval_reports (
    report_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    report_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_eval_reports_created ON eval_reports(created_at DESC);

CREATE TABLE IF NOT EXISTS eval_ab_tests (
    test_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    baseline_variant TEXT NOT NULL,
    candidate_variant TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_eval_ab_status ON eval_ab_tests(status);
"""


def init_evaluation_db() -> None:
    _ensure_memory_db()
    with connect() as conn:
        conn.executescript(EVAL_SCHEMA)
        conn.commit()


init_evaluation_db()
