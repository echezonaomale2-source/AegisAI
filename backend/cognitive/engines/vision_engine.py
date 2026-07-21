"""Engine 1 — Vision Engine: screenshots → ChartModel."""

from __future__ import annotations

from pathlib import Path

from cognitive.events import EVT_VISION_DONE, EventBus
from core.logging_setup import get_logger
from core.models.chart import ChartModel
from core.reconstruction import ChartReconstructor
from core.services import ImageService

log = get_logger("cognitive.vision")


class CognitiveVisionEngine:
    """
    Convert screenshots into structured chart information.

    Wraps Phase 5/5.5 validation + reconstruction — does not rewrite CV.
    """

    def __init__(
        self,
        reconstructor: ChartReconstructor | None = None,
        image_service: ImageService | None = None,
        bus: EventBus | None = None,
    ) -> None:
        self._reconstructor = reconstructor or ChartReconstructor()
        self._images = image_service or ImageService()
        self._bus = bus

    def process(
        self,
        path: str | Path,
        *,
        expected_timeframe: str | None = None,
        pair: str | None = None,
    ) -> ChartModel:
        quality = self._images.validate(path)
        if not quality.ok:
            model = ChartModel(
                status="error",
                error=quality.message or "Image Quality Too Low",
                image_quality_score=quality.quality_score,
                source_image_path=str(path),
                notes=[quality.message or "Image Quality Too Low"],
            )
            if self._bus:
                self._bus.publish(EVT_VISION_DONE, {"status": "error", "path": str(path)})
            return model

        model = self._reconstructor.reconstruct(
            path, expected_timeframe=expected_timeframe, pair=pair
        )
        log.info(
            "vision done path=%s status=%s quality=%.1f candles=%d",
            path,
            model.status,
            model.image_quality_score,
            len(model.candles),
        )
        if self._bus:
            self._bus.publish(
                EVT_VISION_DONE,
                {
                    "status": model.status,
                    "path": str(path),
                    "quality": model.image_quality_score,
                    "timeframe": model.timeframe,
                },
            )
        return model
