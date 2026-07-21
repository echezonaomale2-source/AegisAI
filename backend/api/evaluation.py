"""Evaluation Framework API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from evaluation.dashboard import EvaluationDashboardService
from evaluation.engine import EvaluationEngine
from evaluation.quality_gates import ABTestService, QualityGateService

router = APIRouter(tags=["evaluation"])
engine = EvaluationEngine()
dashboard = EvaluationDashboardService()
gates = QualityGateService()
ab = ABTestService()


class GateRequest(BaseModel):
    gate_name: str = "module_update"
    baseline_score: float
    candidate_score: float
    min_improvement: float = 2.0


class ABStartRequest(BaseModel):
    name: str
    baseline_variant: str = "default"
    candidate_variant: str


class ABCompleteRequest(BaseModel):
    baseline_score: float
    candidate_score: float
    min_improvement: float = 2.0
    baseline_metrics: dict = Field(default_factory=dict)
    candidate_metrics: dict = Field(default_factory=dict)


@router.get("/evaluation/dashboard")
async def evaluation_dashboard() -> dict:
    return dashboard.build().model_dump(mode="json")


@router.get("/evaluation/report")
async def evaluation_report(persist: bool = True) -> dict:
    return engine.build_report(persist=persist).model_dump(mode="json")


@router.get("/evaluation/reports")
async def list_evaluation_reports(limit: int = 10) -> dict:
    reports = engine.list_reports(limit=limit)
    return {"reports": [r.model_dump(mode="json") for r in reports]}


@router.get("/evaluation/health")
async def evaluation_health() -> dict:
    report = engine.build_report(persist=False)
    return report.health.model_dump(mode="json")


@router.get("/evaluation/paths")
async def decision_paths(limit: int = 20) -> dict:
    return {"paths": engine.paths.recent(limit)}


@router.post("/evaluation/gates/check")
async def check_quality_gate(body: GateRequest) -> dict:
    result = gates.evaluate(
        gate_name=body.gate_name,
        baseline_score=body.baseline_score,
        candidate_score=body.candidate_score,
        min_improvement=body.min_improvement,
    )
    return result.model_dump(mode="json")


@router.post("/evaluation/ab/start")
async def ab_start(body: ABStartRequest) -> dict:
    record = ab.start(
        body.name,
        baseline_variant=body.baseline_variant,
        candidate_variant=body.candidate_variant,
    )
    return record.model_dump(mode="json")


@router.post("/evaluation/ab/{test_id}/complete")
async def ab_complete(test_id: str, body: ABCompleteRequest) -> dict:
    try:
        record = ab.complete(
            test_id,
            baseline_score=body.baseline_score,
            candidate_score=body.candidate_score,
            baseline_metrics=body.baseline_metrics,
            candidate_metrics=body.candidate_metrics,
            min_improvement=body.min_improvement,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return record.model_dump(mode="json")


@router.get("/evaluation/ab")
async def ab_list(limit: int = 20) -> dict:
    return {"tests": [t.model_dump(mode="json") for t in ab.list_tests(limit)]}
