from fastapi import APIRouter

from config.settings import settings
from models.schemas import HealthResponse, utc_now_iso

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        version=settings.app_version,
        timestamp=utc_now_iso(),
    )
