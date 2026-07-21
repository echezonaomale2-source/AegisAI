"""
Application-level dependency injection for FastAPI entry points.

Keeps routers free of ad-hoc service construction while preserving existing
module constructors for tests.
"""

from __future__ import annotations

from functools import lru_cache

from brain.coordinator import AIBrain
from core.container import ServiceContainer, get_container
from core.logging_setup import get_logger
from memory.memory_service import MemoryService
from research.dashboard import ResearchDashboardService
from research.orchestrator import ResearchOrchestrator
from services.analysis_service import AnalysisService
from storage.trade_store import TradeStore
from verification.discrepancy import DiscrepancyReporter
from verification.engine import VerificationEngine
from verification.provider import NullMarketDataProvider

log = get_logger("app_deps")


class AppServices:
    """Singleton-ish holder for API-layer services."""

    def __init__(self) -> None:
        self.core: ServiceContainer = get_container()
        self.trade_store = TradeStore()
        self.memory = MemoryService()
        self.research = ResearchOrchestrator()
        self.research_dashboard = ResearchDashboardService()
        self.verification = VerificationEngine(provider=NullMarketDataProvider())
        self.discrepancy_reporter = DiscrepancyReporter()
        self.brain = AIBrain(
            memory=self.memory,
            research=self.research,
            trade_store=self.trade_store,
            verification=self.verification,
        )
        self.analysis = AnalysisService(brain=self.brain)
        log.info("AppServices ready")


@lru_cache(maxsize=1)
def get_app_services() -> AppServices:
    return AppServices()


def reset_app_services() -> None:
    get_app_services.cache_clear()


def get_analysis_service() -> AnalysisService:
    return get_app_services().analysis


def get_brain() -> AIBrain:
    return get_app_services().brain


def get_trade_store() -> TradeStore:
    return get_app_services().trade_store


def get_memory_service() -> MemoryService:
    return get_app_services().memory


def get_research() -> ResearchOrchestrator:
    return get_app_services().research


def get_research_dashboard() -> ResearchDashboardService:
    return get_app_services().research_dashboard
