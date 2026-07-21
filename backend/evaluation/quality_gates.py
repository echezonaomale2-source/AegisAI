"""
Quality gates and A/B testing.

A module update is accepted only when evaluation shows measurable improvement.
Historical evaluation reports are retained.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from models.schemas import utc_now_iso
from memory.database import connect
from evaluation.database import init_evaluation_db
from evaluation.models import ABTestRecord, QualityGateResult

init_evaluation_db()

DEFAULT_MIN_IMPROVEMENT = 2.0  # absolute score points


class QualityGateService:
    def evaluate(
        self,
        *,
        gate_name: str,
        baseline_score: float,
        candidate_score: float,
        min_improvement: float = DEFAULT_MIN_IMPROVEMENT,
        evidence: dict[str, Any] | None = None,
    ) -> QualityGateResult:
        delta = candidate_score - baseline_score
        accepted = delta >= min_improvement
        reason = (
            f"Candidate improved by {delta:.2f} (≥ {min_improvement})."
            if accepted
            else f"Candidate delta {delta:.2f} below required improvement {min_improvement}."
        )
        return QualityGateResult(
            accepted=accepted,
            gate_name=gate_name,
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            delta=round(delta, 3),
            min_improvement=min_improvement,
            reason=reason,
            evidence=evidence or {},
        )


class ABTestService:
    def __init__(self) -> None:
        self.gates = QualityGateService()

    def start(
        self,
        name: str,
        *,
        baseline_variant: str = "default",
        candidate_variant: str,
    ) -> ABTestRecord:
        now = utc_now_iso()
        record = ABTestRecord(
            test_id=str(uuid.uuid4()),
            name=name,
            baseline_variant=baseline_variant,
            candidate_variant=candidate_variant,
            status="running",
            created_at=now,
        )
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO eval_ab_tests
                (test_id, name, baseline_variant, candidate_variant, status, payload_json, created_at, completed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                (
                    record.test_id,
                    name,
                    baseline_variant,
                    candidate_variant,
                    "running",
                    record.model_dump_json(),
                    now,
                ),
            )
            conn.commit()
        return record

    def complete(
        self,
        test_id: str,
        *,
        baseline_score: float,
        candidate_score: float,
        baseline_metrics: dict[str, Any] | None = None,
        candidate_metrics: dict[str, Any] | None = None,
        min_improvement: float = DEFAULT_MIN_IMPROVEMENT,
    ) -> ABTestRecord:
        gate = self.gates.evaluate(
            gate_name=f"ab:{test_id}",
            baseline_score=baseline_score,
            candidate_score=candidate_score,
            min_improvement=min_improvement,
            evidence={
                "baseline_metrics": baseline_metrics or {},
                "candidate_metrics": candidate_metrics or {},
            },
        )
        now = utc_now_iso()
        with connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM eval_ab_tests WHERE test_id = ?",
                (test_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"A/B test not found: {test_id}")
            record = ABTestRecord.model_validate_json(row["payload_json"])
            record.baseline_metrics = baseline_metrics or {}
            record.candidate_metrics = candidate_metrics or {}
            record.gate_result = gate
            record.status = "accepted" if gate.accepted else "rejected"
            record.completed_at = now
            conn.execute(
                """
                UPDATE eval_ab_tests
                SET status = ?, payload_json = ?, completed_at = ?
                WHERE test_id = ?
                """,
                (record.status, record.model_dump_json(), now, test_id),
            )
            conn.commit()
        return record

    def list_tests(self, limit: int = 20) -> list[ABTestRecord]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT payload_json FROM eval_ab_tests ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [ABTestRecord.model_validate_json(r["payload_json"]) for r in rows]
