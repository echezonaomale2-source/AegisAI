from fastapi import APIRouter, File, Form, UploadFile

from cv.models import VisionChartResult, VisionMultiResult
from cv.vision_engine import VisionEngine
from storage.file_storage import save_upload

router = APIRouter(tags=["vision"])
engine = VisionEngine(use_cache=True)


@router.post("/vision/chart", response_model=VisionChartResult)
async def vision_single_chart(
    chart: UploadFile = File(..., description="Single chart screenshot"),
    expected_timeframe: str | None = Form(default=None),
    pair: str | None = Form(default=None),
) -> VisionChartResult:
    """Visual understanding only — candles, features, structure graph (no OCR)."""
    saved = await save_upload(chart, "vision")
    return engine.analyze_chart(
        saved, expected_timeframe=expected_timeframe, pair=pair
    )


@router.post("/vision/multi", response_model=VisionMultiResult)
async def vision_multi_charts(
    chart_4h: UploadFile = File(...),
    chart_1h: UploadFile = File(...),
    chart_15m: UploadFile = File(...),
    pair: str = Form(default="EURUSD"),
    timeframe_htf: str = Form(default="4H"),
    timeframe_mtf: str = Form(default="1H"),
    timeframe_ltf: str = Form(default="15M"),
) -> VisionMultiResult:
    """Independent TF vision + relationship graph (no trade bias, no OCR)."""
    saved_4h = await save_upload(chart_4h, "4h")
    saved_1h = await save_upload(chart_1h, "1h")
    saved_15m = await save_upload(chart_15m, "15m")
    return engine.analyze_multi(
        saved_4h,
        saved_1h,
        saved_15m,
        pair=pair,
        timeframe_htf=timeframe_htf,
        timeframe_mtf=timeframe_mtf,
        timeframe_ltf=timeframe_ltf,
    )
