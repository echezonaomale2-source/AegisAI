from fastapi import APIRouter, File, Form, UploadFile

from models.chart_schemas import ChartAnalysis, MultiChartAnalysis
from services.chart_analysis_service import ChartAnalysisService
from services.multi_analysis_service import MultiChartAnalysisService
from storage.file_storage import save_upload

router = APIRouter(tags=["chart-analysis"])
chart_service = ChartAnalysisService()
multi_service = MultiChartAnalysisService()


@router.post("/analyze/chart", response_model=ChartAnalysis)
async def analyze_single_chart(
    chart: UploadFile = File(..., description="Single chart screenshot"),
    expected_timeframe: str | None = Form(default=None),
) -> ChartAnalysis:
    saved = await save_upload(chart, "single")
    return chart_service.analyze(saved, expected_timeframe=expected_timeframe)


@router.post("/analyze/multi", response_model=MultiChartAnalysis)
async def analyze_multi_charts(
    chart_4h: UploadFile = File(..., description="4H chart image"),
    chart_1h: UploadFile = File(..., description="1H chart image"),
    chart_15m: UploadFile = File(..., description="15M chart image"),
) -> MultiChartAnalysis:
    saved_4h = await save_upload(chart_4h, "4h")
    saved_1h = await save_upload(chart_1h, "1h")
    saved_15m = await save_upload(chart_15m, "15m")
    return multi_service.analyze(saved_4h, saved_1h, saved_15m)
