from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time
import uuid

from api.analyze import router as analyze_router
from api.brain import router as brain_router
from api.chart_analyze import router as chart_analyze_router
from api.cognitive import router as cognitive_router
from api.dataset import router as dataset_router
from api.decision import router as decision_router
from api.evaluation import router as evaluation_router
from api.health import router as health_router
from api.knowledge import router as knowledge_router
from api.verification import router as verification_router
from api.vision import router as vision_router
from config.settings import settings
from core.logging_setup import configure_logging, get_logger

configure_logging(
    level=settings.log_level,
    log_to_file=settings.log_to_file,
    log_file=str(settings.log_file) if settings.log_to_file else None,
)
log = get_logger("main")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        from core.analysis_jobs import AnalysisJobStore

        n = AnalysisJobStore().recover_stale(mark_failed=True)
        if n:
            log.warning("marked %s interrupted analysis job(s) as failed", n)
    except Exception as exc:  # noqa: BLE001
        log.debug("job recovery skipped: %s", exc)
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "AegisAI personal smart-money trading assistant API. "
        "Production roadmap complete — personal-use hardened."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
    start = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception(
            "unhandled error request_id=%s %s %s",
            request_id,
            request.method,
            request.url.path,
        )
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id,
            },
        )
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Request-ID"] = request_id
    log.info(
        "request_id=%s %s %s status=%s %.1fms",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


app.include_router(health_router, prefix="/api")
app.include_router(analyze_router, prefix="/api")
app.include_router(chart_analyze_router, prefix="/api")
app.include_router(decision_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(cognitive_router, prefix="/api")
app.include_router(knowledge_router, prefix="/api")
app.include_router(evaluation_router, prefix="/api")
app.include_router(brain_router, prefix="/api")
app.include_router(verification_router, prefix="/api")
app.include_router(dataset_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
    }


log.info(
    "AegisAI %s starting storage=%s encrypt_trades=%s",
    settings.app_version,
    settings.storage_root,
    settings.encrypt_trade_records,
)
