"""AI Brain API — full recommendation with reason trace."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile

from brain.coordinator import AIBrain
from core.app_deps import get_brain
from core.logging_setup import get_logger
from storage.file_storage import save_upload

router = APIRouter(tags=["brain"])
log = get_logger("api.brain")


@router.post("/brain/recommend")
async def brain_recommend(
    chart_4h: UploadFile = File(...),
    chart_1h: UploadFile = File(...),
    chart_15m: UploadFile = File(...),
    pair: str = Form(default="UNKNOWN"),
    persist: bool = Form(default=False),
    brain: AIBrain = Depends(get_brain),
) -> dict:
    """
    Single entry point for trading recommendations via the AI Brain.

    Returns TradeDecision fields plus BrainRecommendation (trace, historical support).
    """
    p4 = await save_upload(chart_4h, "4h")
    p1 = await save_upload(chart_1h, "1h")
    p15 = await save_upload(chart_15m, "15m")
    log.info("brain recommend pair=%s persist=%s", pair, persist)
    decision, recommendation = brain.recommend_detailed(
        pair=pair,
        chart_4h=p4,
        chart_1h=p1,
        chart_15m=p15,
        persist=persist,
    )
    return {
        "decision": decision.model_dump(mode="json"),
        "brain": recommendation.model_dump(mode="json"),
    }
