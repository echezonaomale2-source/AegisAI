"""Decision path logger — immutable audit trail for every recommendation."""

from __future__ import annotations

import json
import uuid
from typing import Any

from models.schemas import utc_now_iso
from memory.database import connect
from evaluation.database import init_evaluation_db
from evaluation.models import DecisionPathLog

init_evaluation_db()


class DecisionPathLogger:
    def log(
        self,
        *,
        trade_id: str | None,
        input_summary: dict[str, Any],
        validated_concepts: list[str],
        evidence_summary: dict[str, Any],
        reasoning_summary: dict[str, Any],
        decision: str,
        confidence: float,
        knowledge_version: str | None = None,
        variant_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> DecisionPathLog:
        now = utc_now_iso()
        entry = DecisionPathLog(
            log_id=str(uuid.uuid4()),
            trade_id=trade_id,
            timestamp=now,
            input_summary=input_summary,
            validated_concepts=validated_concepts,
            evidence_summary=evidence_summary,
            reasoning_summary=reasoning_summary,
            decision=decision,
            confidence=confidence,
            knowledge_version=knowledge_version,
            variant_id=variant_id,
            metadata=metadata or {},
        )
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_decision_paths
                (log_id, trade_id, timestamp, decision, confidence, knowledge_version,
                 variant_id, payload_json, outcome, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?)
                """,
                (
                    entry.log_id,
                    trade_id,
                    now,
                    decision,
                    confidence,
                    knowledge_version,
                    variant_id,
                    entry.model_dump_json(),
                    now,
                ),
            )
            conn.commit()
        return entry

    def attach_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        review_scores: dict[str, Any] | None = None,
    ) -> int:
        """Update path logs for a trade with outcome + review scores (append-only fields)."""
        with connect() as conn:
            rows = conn.execute(
                "SELECT log_id, payload_json FROM eval_decision_paths WHERE trade_id = ?",
                (trade_id,),
            ).fetchall()
            updated = 0
            for row in rows:
                payload = json.loads(row["payload_json"])
                payload["outcome"] = outcome
                if review_scores is not None:
                    payload["review_scores"] = review_scores
                conn.execute(
                    """
                    UPDATE eval_decision_paths
                    SET outcome = ?, payload_json = ?
                    WHERE log_id = ?
                    """,
                    (outcome, json.dumps(payload, default=str), row["log_id"]),
                )
                updated += 1
            conn.commit()
        return updated

    def count(self) -> int:
        with connect() as conn:
            return int(conn.execute("SELECT COUNT(*) AS c FROM eval_decision_paths").fetchone()["c"])

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT payload_json FROM eval_decision_paths
                ORDER BY timestamp DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [json.loads(r["payload_json"]) for r in rows]
