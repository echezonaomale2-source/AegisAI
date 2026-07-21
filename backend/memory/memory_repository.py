"""Trade memory repository — permanent CRUD over SQLite memories."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from memory.database import connect
from memory.outcome_utils import status_code
from memory.secure_fields import (
    SENSITIVE_MEMORY_COLUMNS,
    SENSITIVE_REVIEW_COLUMNS,
    seal_json_dump,
    seal_text,
    unseal_row,
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryRepository:
    def upsert_memory(self, record: dict[str, Any]) -> None:
        now = _utc_now()
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (
                    trade_id, timestamp, pair, timeframes_json,
                    chart_4h_path, chart_1h_path, chart_15m_path,
                    features_json, analysis_4h_json, analysis_1h_json, analysis_15m_json,
                    final_decision, entry, stop_loss, take_profit, risk_reward,
                    confidence, explanation, status, outcome, outcome_chart_path,
                    lesson, fingerprint_bits, fingerprint_hash, direction,
                    closed_at, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(trade_id) DO UPDATE SET
                    timestamp=excluded.timestamp,
                    pair=excluded.pair,
                    timeframes_json=excluded.timeframes_json,
                    chart_4h_path=excluded.chart_4h_path,
                    chart_1h_path=excluded.chart_1h_path,
                    chart_15m_path=excluded.chart_15m_path,
                    features_json=excluded.features_json,
                    analysis_4h_json=excluded.analysis_4h_json,
                    analysis_1h_json=excluded.analysis_1h_json,
                    analysis_15m_json=excluded.analysis_15m_json,
                    final_decision=excluded.final_decision,
                    entry=excluded.entry,
                    stop_loss=excluded.stop_loss,
                    take_profit=excluded.take_profit,
                    risk_reward=excluded.risk_reward,
                    confidence=excluded.confidence,
                    explanation=excluded.explanation,
                    status=excluded.status,
                    fingerprint_bits=excluded.fingerprint_bits,
                    fingerprint_hash=excluded.fingerprint_hash,
                    direction=excluded.direction,
                    updated_at=excluded.updated_at
                """,
                (
                    record["trade_id"],
                    record["timestamp"],
                    record["pair"],
                    json.dumps(record.get("timeframes", {})),
                    record.get("chart_4h_path"),
                    record.get("chart_1h_path"),
                    record.get("chart_15m_path"),
                    seal_json_dump(record.get("features", {})),
                    seal_json_dump(record.get("analysis_4h", {})),
                    seal_json_dump(record.get("analysis_1h", {})),
                    seal_json_dump(record.get("analysis_15m", {})),
                    record["final_decision"],
                    record.get("entry"),
                    record.get("stop_loss"),
                    record.get("take_profit"),
                    record.get("risk_reward"),
                    record.get("confidence", 0),
                    seal_text(record.get("explanation")),
                    record.get("status", "Waiting Result"),
                    record.get("outcome"),
                    record.get("outcome_chart_path"),
                    seal_text(record.get("lesson")),
                    record["fingerprint_bits"],
                    record["fingerprint_hash"],
                    record.get("direction", "NO TRADE"),
                    record.get("closed_at"),
                    now,
                    now,
                ),
            )
            conn.commit()

    def update_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart_path: str | None,
        lesson: str,
        grade: str | None = None,
        review_json: str | None = None,
        lessons_json: str | None = None,
        pattern_key: str | None = None,
    ) -> dict[str, Any] | None:
        now = _utc_now()
        with connect() as conn:
            conn.execute(
                """
                UPDATE memories
                SET outcome = ?,
                    outcome_chart_path = ?,
                    lesson = ?,
                    status = ?,
                    closed_at = ?,
                    updated_at = ?,
                    grade = COALESCE(?, grade),
                    review_json = COALESCE(?, review_json),
                    lessons_json = COALESCE(?, lessons_json),
                    pattern_key = COALESCE(?, pattern_key)
                WHERE trade_id = ?
                """,
                (
                    outcome,
                    outcome_chart_path,
                    seal_text(lesson),
                    status_code(outcome),
                    now,
                    now,
                    grade,
                    seal_text(review_json) if review_json is not None else None,
                    seal_text(lessons_json) if lessons_json is not None else None,
                    pattern_key,
                    trade_id,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM memories WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
        return unseal_row(dict(row), SENSITIVE_MEMORY_COLUMNS) if row else None

    def save_review(
        self,
        trade_id: str,
        *,
        grade: str,
        scorecard: dict,
        critique: dict,
        questions: dict,
        lessons: list[str],
        summary: str,
        outcome_analysis: dict | None,
    ) -> None:
        now = _utc_now()
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO reviews (
                    trade_id, grade, scorecard_json, critique_json, questions_json,
                    lessons_json, summary, outcome_analysis_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(trade_id) DO UPDATE SET
                    grade=excluded.grade,
                    scorecard_json=excluded.scorecard_json,
                    critique_json=excluded.critique_json,
                    questions_json=excluded.questions_json,
                    lessons_json=excluded.lessons_json,
                    summary=excluded.summary,
                    outcome_analysis_json=excluded.outcome_analysis_json,
                    created_at=excluded.created_at
                """,
                (
                    trade_id,
                    grade,
                    seal_json_dump(scorecard),
                    seal_json_dump(critique),
                    seal_json_dump(questions),
                    seal_json_dump(lessons),
                    seal_text(summary),
                    seal_json_dump(outcome_analysis) if outcome_analysis else None,
                    now,
                ),
            )
            conn.commit()

    def get(self, trade_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM memories WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
        return unseal_row(dict(row), SENSITIVE_MEMORY_COLUMNS) if row else None

    def get_review(self, trade_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM reviews WHERE trade_id = ?",
                (trade_id,),
            ).fetchone()
        return unseal_row(dict(row), SENSITIVE_REVIEW_COLUMNS) if row else None

    def count(self) -> int:
        with connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"])

    def closed_stats(self) -> dict[str, Any]:
        with connect() as conn:
            total = int(conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"])
            wins = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE outcome = 'TAKE_PROFIT'"
                ).fetchone()["c"]
            )
            losses = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE outcome = 'STOP_LOSS'"
                ).fetchone()["c"]
            )
            waiting = int(
                conn.execute(
                    "SELECT COUNT(*) AS c FROM memories WHERE outcome IS NULL"
                ).fetchone()["c"]
            )
            last = conn.execute(
                "SELECT meta_value FROM learning_meta WHERE meta_key = 'last_learning_update'"
            ).fetchone()
            top_pair = conn.execute(
                """
                SELECT pair, COUNT(*) AS c
                FROM memories
                WHERE outcome = 'TAKE_PROFIT'
                GROUP BY pair
                ORDER BY c DESC
                LIMIT 1
                """
            ).fetchone()
        closed = wins + losses
        return {
            "total_trades_stored": total,
            "winning_trades": wins,
            "losing_trades": losses,
            "waiting_trades": waiting,
            "estimated_win_rate": round(wins / closed * 100, 2) if closed else None,
            "most_successful_pair": top_pair["pair"] if top_pair else None,
            "last_learning_update": last["meta_value"] if last else "never",
            "total_memories_stored": total,
        }
