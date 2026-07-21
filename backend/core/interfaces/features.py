"""Feature extraction interface."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.models.chart import ChartModel
from core.models.features import FeatureSet


@runtime_checkable
class FeatureExtractorProtocol(Protocol):
    def extract(self, chart: ChartModel) -> FeatureSet:
        """Convert reconstructed chart into structured Feature objects."""
        ...
