"""
AegisAI Research Platform (Phase 7).

Measures analysis quality over time. Does not chase wins.
Explainable calibration, pattern library, post-trade reviews, research dashboard.
"""

from research.orchestrator import ResearchOrchestrator
from research.dashboard import ResearchDashboardService

__all__ = ["ResearchOrchestrator", "ResearchDashboardService"]
