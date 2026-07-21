"""Image validation interface."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field


class ImageQualityReport(BaseModel):
    ok: bool
    quality_score: float = Field(ge=0, le=100, default=0.0)
    sharpness: float = 0.0
    message: str | None = None
    path: str | None = None
    unsupported_format: bool = False


@runtime_checkable
class ImageValidatorProtocol(Protocol):
    def validate(self, path: str | Path) -> ImageQualityReport:
        """Validate screenshot quality; must not invent chart content."""
        ...
