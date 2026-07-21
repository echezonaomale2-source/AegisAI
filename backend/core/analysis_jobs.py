"""Analysis job checkpoints — recover interrupted analyses (Step 15)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from memory.database import connect
from models.schemas import utc_now_iso

ANALYSIS_SCHEMA_VERSION = "1.0"


def ensure_jobs_schema() -> None:
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                pair TEXT,
                chart_4h_path TEXT,
                chart_1h_path TEXT,
                chart_15m_path TEXT,
                trade_id TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                payload_json TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_analysis_jobs_status ON analysis_jobs(status)"
        )
        conn.commit()


ensure_jobs_schema()


class AnalysisJobStore:
    def create(
        self,
        *,
        pair: str,
        chart_4h: Path | str,
        chart_1h: Path | str,
        chart_15m: Path | str,
    ) -> str:
        job_id = uuid.uuid4().hex
        now = utc_now_iso()
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO analysis_jobs
                (job_id, status, pair, chart_4h_path, chart_1h_path, chart_15m_path,
                 trade_id, error, created_at, updated_at, payload_json)
                VALUES (?, 'pending', ?, ?, ?, ?, NULL, NULL, ?, ?, NULL)
                """,
                (job_id, pair, str(chart_4h), str(chart_1h), str(chart_15m), now, now),
            )
            conn.commit()
        return job_id

    def mark_running(self, job_id: str) -> None:
        self._set(job_id, status="running")

    def mark_done(self, job_id: str, *, trade_id: str, payload: dict[str, Any] | None = None) -> None:
        self._set(
            job_id,
            status="done",
            trade_id=trade_id,
            payload_json=json.dumps(payload or {}, default=str),
        )

    def mark_failed(self, job_id: str, error: str) -> None:
        self._set(job_id, status="failed", error=error[:2000])

    def get(self, job_id: str) -> dict[str, Any] | None:
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM analysis_jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return dict(row) if row else None

    def list_interrupted(self, limit: int = 20) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM analysis_jobs
                WHERE status IN ('pending', 'running')
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def recover_stale(self, *, mark_failed: bool = True) -> int:
        """Mark leftover running jobs as failed after crash."""
        jobs = self.list_interrupted()
        if not mark_failed:
            return len(jobs)
        for job in jobs:
            if job["status"] == "running":
                self.mark_failed(job["job_id"], "Interrupted — process crashed or restarted")
        return len(jobs)

    def _set(self, job_id: str, **fields: Any) -> None:
        now = utc_now_iso()
        cols = []
        vals: list[Any] = []
        for key, value in fields.items():
            cols.append(f"{key} = ?")
            vals.append(value)
        cols.append("updated_at = ?")
        vals.append(now)
        vals.append(job_id)
        with connect() as conn:
            conn.execute(
                f"UPDATE analysis_jobs SET {', '.join(cols)} WHERE job_id = ?",
                vals,
            )
            conn.commit()
