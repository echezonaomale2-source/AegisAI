from fastapi import APIRouter, Depends, File, Form, UploadFile

from core.app_deps import get_analysis_service
from core.logging_setup import get_logger
from models.schemas import AnalysisResult
from services.analysis_service import AnalysisService
from storage.file_storage import save_upload

router = APIRouter(tags=["analyze"])
log = get_logger("api.analyze")


@router.post("/analyze", response_model=AnalysisResult)
async def analyze_charts(
    chart_4h: UploadFile = File(..., description="4H chart image"),
    chart_1h: UploadFile = File(..., description="1H chart image"),
    chart_15m: UploadFile = File(..., description="15M chart image"),
    pair: str = Form(default="UNKNOWN"),
    analysis_service: AnalysisService = Depends(get_analysis_service),
) -> AnalysisResult:
    saved_4h = await save_upload(chart_4h, "4h")
    saved_1h = await save_upload(chart_1h, "1h")
    saved_15m = await save_upload(chart_15m, "15m")
    log.info("analyze request pair=%s", pair)

    return analysis_service.analyze(
        pair=pair,
        chart_4h=saved_4h,
        chart_1h=saved_1h,
        chart_15m=saved_15m,
    )
