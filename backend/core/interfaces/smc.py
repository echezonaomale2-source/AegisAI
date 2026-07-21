"""Smart Money Concepts engine interface — reasoning only, no BUY/SELL."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from core.models.analysis import SMCAnalysis
from core.models.chart import ChartModel
from core.models.features import FeatureSet


@runtime_checkable
class SmartMoneyEngineProtocol(Protocol):
    def analyze(self, chart: ChartModel, features: FeatureSet) -> SMCAnalysis:
        """Return structured SMC reasoning (no trade recommendation)."""
        ...
