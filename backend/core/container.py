"""Dependency injection container for core AI services."""

from __future__ import annotations

from functools import lru_cache

from core.cache import IntermediateCache
from core.engines.feature_extractor import FeatureExtractor
from core.engines.smc_engine import SmartMoneyEngine
from core.logging_setup import get_logger
from core.reconstruction import ChartReconstructor
from core.services import (
    ChartService,
    ConfidenceService,
    DecisionService,
    FeatureService,
    ImageService,
    LearningService,
    MemoryService,
    SimilarityService,
    SMCService,
    VisionService,
)
from cv.vision_engine import VisionEngine

log = get_logger("container")


class ServiceContainer:
    """
    Wires interfaces to production implementations.

    Individual engines can be replaced (e.g. GPU vision) by constructing
    a container with alternate dependencies — downstream code stays unchanged.

    Memory / learning are lazy to avoid circular imports with ReviewEngine.
    """

    def __init__(
        self,
        *,
        use_cache: bool = True,
        model_version: str = "core-v1",
        vision_engine: VisionEngine | None = None,
    ) -> None:
        self.cache = IntermediateCache(model_version=model_version, enabled=use_cache)
        self.vision_engine = vision_engine or VisionEngine(use_cache=use_cache)
        self.reconstructor = ChartReconstructor(vision_engine=self.vision_engine)
        self.feature_extractor = FeatureExtractor()
        self.smc_engine = SmartMoneyEngine()

        self.image = ImageService()
        self.chart = ChartService(vision=self.vision_engine)
        self.vision = VisionService(reconstructor=self.reconstructor, cache=self.cache)
        self.features = FeatureService(extractor=self.feature_extractor, cache=self.cache)
        self.smc = SMCService(engine=self.smc_engine)
        self.decision = DecisionService()
        self.confidence = ConfidenceService()
        self._memory: MemoryService | None = None
        self._learning: LearningService | None = None
        self._similarity: SimilarityService | None = None
        log.info("ServiceContainer ready model_version=%s cache=%s", model_version, use_cache)

    @property
    def memory(self) -> MemoryService:
        if self._memory is None:
            self._memory = MemoryService()
        return self._memory

    @property
    def learning(self) -> LearningService:
        if self._learning is None:
            self._learning = LearningService(memory=self.memory)
        return self._learning

    @property
    def similarity(self) -> SimilarityService:
        if self._similarity is None:
            self._similarity = SimilarityService()
        return self._similarity


@lru_cache(maxsize=1)
def get_container() -> ServiceContainer:
    return ServiceContainer()


def reset_container() -> None:
    get_container.cache_clear()
