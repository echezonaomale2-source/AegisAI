"""Atomic evaluation counters and feature event tallies."""

from __future__ import annotations

from models.schemas import utc_now_iso
from memory.database import connect
from evaluation.database import init_evaluation_db

init_evaluation_db()


class EvalCounters:
    def incr(self, key: str, amount: float = 1.0) -> None:
        now = utc_now_iso()
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_counters (counter_key, counter_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(counter_key) DO UPDATE SET
                    counter_value = counter_value + excluded.counter_value,
                    updated_at = excluded.updated_at
                """,
                (key, amount, now),
            )
            conn.commit()

    def get(self, key: str, default: float = 0.0) -> float:
        with connect() as conn:
            row = conn.execute(
                "SELECT counter_value FROM eval_counters WHERE counter_key = ?",
                (key,),
            ).fetchone()
        return float(row["counter_value"]) if row else default

    def all(self) -> dict[str, float]:
        with connect() as conn:
            rows = conn.execute("SELECT counter_key, counter_value FROM eval_counters").fetchall()
        return {r["counter_key"]: float(r["counter_value"]) for r in rows}

    def record_feature(self, feature_key: str, *, detected: bool = True, unknown: bool = False) -> None:
        now = utc_now_iso()
        det = 1 if detected else 0
        unk = 1 if unknown else 0
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_feature_events (feature_key, detections, unknowns, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(feature_key) DO UPDATE SET
                    detections = detections + excluded.detections,
                    unknowns = unknowns + excluded.unknowns,
                    updated_at = excluded.updated_at
                """,
                (feature_key, det, unk, now),
            )
            conn.commit()

    def feature_events(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT feature_key, detections, unknowns FROM eval_feature_events ORDER BY detections DESC"
            ).fetchall()
        return [dict(r) for r in rows]
