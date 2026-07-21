from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from core.app_deps import (
    get_analysis_service,
    get_memory_service,
    get_research,
    get_research_dashboard,
    get_trade_store,
)
from core.logging_setup import get_logger
from memory.memory_service import MemoryService
from models.decision_schemas import TradeDecision
from research.dashboard import ResearchDashboardService
from research.orchestrator import ResearchOrchestrator
from services.analysis_service import AnalysisService
from storage.file_storage import save_upload
from storage.trade_store import TradeStore

router = APIRouter(tags=["decision-memory"])
log = get_logger("api.decision")


@router.post("/decide", response_model=TradeDecision)
async def decide_trade(
    chart_4h: UploadFile = File(..., description="Higher timeframe chart image"),
    chart_1h: UploadFile = File(..., description="Middle timeframe chart image"),
    chart_15m: UploadFile = File(..., description="Entry timeframe chart image"),
    pair: str = Form(default="EURUSD"),
    timeframe_htf: str = Form(default="4H"),
    timeframe_mtf: str = Form(default="1H"),
    timeframe_ltf: str = Form(default="15M"),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> TradeDecision:
    """Top-down SMC decision engine with memory-adjusted confidence."""
    saved_4h = await save_upload(chart_4h, "4h")
    saved_1h = await save_upload(chart_1h, "1h")
    saved_15m = await save_upload(chart_15m, "15m")
    log.info(
        "decide request pair=%s htf=%s mtf=%s ltf=%s",
        pair,
        timeframe_htf,
        timeframe_mtf,
        timeframe_ltf,
    )
    return analysis_service.decide(
        pair=pair,
        chart_4h=saved_4h,
        chart_1h=saved_1h,
        chart_15m=saved_15m,
        timeframe_htf=timeframe_htf,
        timeframe_mtf=timeframe_mtf,
        timeframe_ltf=timeframe_ltf,
        persist=True,
    )


@router.post("/trades/{trade_id}/outcome")
async def submit_trade_outcome(
    trade_id: str,
    outcome: str = Form(..., description="TAKE_PROFIT or STOP_LOSS"),
    result_chart: UploadFile = File(..., description="Final result screenshot"),
    comments: str = Form(default=""),
    rr_achieved: str = Form(default=""),
    trade_store: TradeStore = Depends(get_trade_store),
    memory_service: MemoryService = Depends(get_memory_service),
    research: ResearchOrchestrator = Depends(get_research),
) -> dict:
    """Record TP/SL, generate lesson, and run the learning engine."""
    outcome = outcome.strip().upper()
    if outcome not in {"TAKE_PROFIT", "STOP_LOSS", "TP", "SL", "BREAK_EVEN", "BE"}:
        raise HTTPException(
            status_code=400,
            detail="outcome must be TAKE_PROFIT, STOP_LOSS, or BREAK_EVEN",
        )
    if outcome == "TP":
        outcome = "TAKE_PROFIT"
    if outcome == "SL":
        outcome = "STOP_LOSS"
    if outcome == "BE":
        outcome = "BREAK_EVEN"

    # Learning path: BREAK_EVEN is neutral — never treat as a win.
    if trade_store.get_trade(trade_id) is None and memory_service.repo.get(trade_id) is None:
        raise HTTPException(status_code=404, detail="Trade not found")

    saved = await save_upload(result_chart, "outcome")
    log.info("outcome trade_id=%s outcome=%s", trade_id, outcome)
    learned = research.process_outcome(
        trade_id,
        outcome=outcome,
        outcome_chart_path=str(saved),
    )
    try:
        payload = trade_store.update_outcome(
            trade_id,
            outcome=outcome,
            outcome_chart=saved,
            lesson=learned.get("lesson")
            or (
                (learned.get("research") or {}).get("lessons") or [None]
            )[0],
        )
        if comments or rr_achieved:
            # Persist optional notes onto the decision record
            from pathlib import Path

            decision_path = trade_store.root / trade_id / "decision.json"
            if decision_path.exists():
                data = trade_store._read_decision(decision_path)  # noqa: SLF001
                data["comments"] = comments
                data["rr_achieved"] = rr_achieved
                if outcome == "BREAK_EVEN":
                    data["outcome"] = "BREAK_EVEN"
                    data["status"] = "BE"
                trade_store._write_decision(decision_path, data)  # noqa: SLF001
                payload = data
    except FileNotFoundError:
        pass

    research_block = learned.get("research") or {}
    return {
        "status": "learned",
        "trade_id": trade_id,
        "outcome": outcome,
        "comments": comments,
        "rr_achieved": rr_achieved,
        "lesson": learned.get("lesson"),
        "lessons": research_block.get("lessons") or learned.get("lessons", []),
        "grade": learned.get("grade"),
        "grade_label": learned.get("grade_label"),
        "decision_quality": research_block.get("decision_quality"),
        "scorecard": research_block.get("scorecard") or learned.get("scorecard"),
        "research_scorecard": research_block.get("scorecard"),
        "critique": learned.get("critique"),
        "questions": research_block.get("questions") or learned.get("questions"),
        "review_summary": (research_block.get("review") or {}).get("summary")
        or learned.get("review_summary"),
        "strengths": research_block.get("strengths"),
        "weaknesses": research_block.get("weaknesses"),
        "pattern": research_block.get("pattern") or learned.get("pattern"),
        "calibration": research_block.get("calibration"),
        "adaptive_weights": learned.get("learning_update"),
        "learning_applied": learned.get("learning_applied", True),
        "learning_skipped": learned.get("skipped", False),
    }


@router.get("/learning/summary")
async def learning_summary(
    research: ResearchOrchestrator = Depends(get_research),
) -> dict:
    """Historical learning snapshot — patterns, calibration, feature reliability."""
    return research.learning_summary()


@router.get("/trades")
async def list_trades(
    trade_store: TradeStore = Depends(get_trade_store),
) -> list[dict]:
    return trade_store.list_trades()


@router.get("/trades/{trade_id}")
async def get_trade(
    trade_id: str,
    trade_store: TradeStore = Depends(get_trade_store),
    memory_service: MemoryService = Depends(get_memory_service),
) -> dict:
    record = trade_store.get_trade(trade_id)
    if record is None:
        memory = memory_service.repo.get(trade_id)
        if memory is None:
            raise HTTPException(status_code=404, detail="Trade not found")
        return memory
    return record


@router.get("/memory/stats")
async def memory_stats(
    memory_service: MemoryService = Depends(get_memory_service),
) -> dict:
    return memory_service.get_stats()


@router.get("/research/dashboard")
async def research_dashboard(
    dashboard: ResearchDashboardService = Depends(get_research_dashboard),
) -> dict:
    return dashboard.build().model_dump(mode="json")
