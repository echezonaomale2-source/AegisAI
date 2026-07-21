"""Phase 6 cognitive reasoning API — transparent evidence trail (no black box)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel, Field

from cognitive.engines.decision_engine import CognitiveDecisionEngine
from cognitive.engines.evidence_engine import EvidenceEngine
from cognitive.engines.reasoning_engine import ReasoningEngine
from cognitive.models.evidence import Evidence
from cognitive.models.features import FeatureCollection
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from cognitive.pipeline import CognitivePipeline
from storage.file_storage import save_upload

router = APIRouter(tags=["cognitive"])
pipeline = CognitivePipeline()
_evidence = EvidenceEngine()
_reasoning = ReasoningEngine()
_decision = CognitiveDecisionEngine()


class EvidenceEvaluateRequest(BaseModel):
    features: FeatureCollection
    image_quality: float = Field(default=100.0, ge=0, le=100)
    feature_weights: dict[str, float] | None = None
    pair: str = "Unknown"


class ReasonFromEvidenceRequest(BaseModel):
    evidence_by_tf: dict[str, Evidence]
    pair: str = "Unknown"
    historical_bias: float = 0.0


class DecideFromReasoningRequest(BaseModel):
    reasoning: ReasoningReport
    risk: RiskAssessment | None = None
    pair: str = "Unknown"


@router.post("/cognitive/reason")
async def cognitive_reason(
    chart_4h: UploadFile = File(...),
    chart_1h: UploadFile = File(...),
    chart_15m: UploadFile = File(...),
    pair: str = Form(default="UNKNOWN"),
) -> dict:
    """
    Full cognitive pass: MarketModel → Evidence → ReasoningReport → Decision.

    Does not persist. Returns explainable scores and trace.
    """
    p4 = await save_upload(chart_4h, "4h")
    p1 = await save_upload(chart_1h, "1h")
    p15 = await save_upload(chart_15m, "15m")
    markets, report, decision = pipeline.reason_multi(
        chart_4h=p4,
        chart_1h=p1,
        chart_15m=p15,
        pair=pair,
    )
    return {
        "pair": decision.pair,
        "recommendation": decision.recommendation,
        "confidence": decision.confidence,
        "trade_grade": decision.trade_grade,
        "entry": decision.entry,
        "stop_loss": decision.stop_loss,
        "take_profit": decision.take_profit,
        "risk_reward": decision.risk_reward,
        "explanation": decision.explanation,
        "reasons": decision.reasons,
        "warnings": decision.warnings,
        "reproducible_hash": decision.reproducible_hash,
        "reasoning": report.model_dump(mode="json"),
        "risk": decision.risk.model_dump(mode="json") if decision.risk else None,
        "markets": {
            tf: {
                "status": m.status,
                "trend": m.trend.direction,
                "structure": m.structure_label,
                "bos": m.bos,
                "choch": m.choch,
                "candle_count": len(m.candles),
                "quality": m.image_quality_score,
            }
            for tf, m in markets.items()
        },
    }


@router.post("/cognitive/evidence/evaluate")
async def cognitive_evidence_evaluate(body: EvidenceEvaluateRequest) -> dict[str, Any]:
    """
    Convert a (Knowledge-validated) FeatureCollection into structured Evidence
    plus an explainable EvidenceReport.
    """
    evidence = _evidence.evaluate(
        body.features,
        image_quality=body.image_quality,
        feature_weights=body.feature_weights,
    )
    report = _evidence.report(
        evidence,
        timeframe=body.features.timeframe,
        pair=body.pair or body.features.pair or "Unknown",
    )
    return {
        "evidence": evidence.model_dump(mode="json"),
        "report": report.model_dump(mode="json"),
    }


@router.post("/cognitive/reasoning/from-evidence")
async def cognitive_reason_from_evidence(body: ReasonFromEvidenceRequest) -> dict[str, Any]:
    """
    Consume multi-TF Evidence → explainable ReasoningReport.
    Prefers NO TRADE when evidence is insufficient or conflicting.
    """
    report = _reasoning.reason(
        body.evidence_by_tf,
        historical_bias=body.historical_bias,
        pair=body.pair,
    )
    return {"reasoning": report.model_dump(mode="json")}


@router.post("/cognitive/decision/from-reasoning")
async def cognitive_decision_from_reasoning(body: DecideFromReasoningRequest) -> dict[str, Any]:
    """
    Produce BUY / SELL / NO TRADE with entry, SL, TP, RR, confidence,
    trade grade, warnings, and detailed explanation.
    """
    risk = body.risk or RiskAssessment(
        risk_grade="F",
        valid=False,
        notes=["No risk plan supplied — Decision Engine will not invent levels."],
    )
    decision = _decision.decide(body.reasoning, risk, pair=body.pair)
    return {"decision": decision.model_dump(mode="json")}
