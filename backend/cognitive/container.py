"""Dependency injection for cognitive engines."""

from __future__ import annotations

from functools import lru_cache

from cognitive.engines import (
    ChartReconstructionEngine,
    CognitiveDecisionEngine,
    CognitiveLearningEngine,
    CognitiveMemoryEngine,
    CognitiveRiskEngine,
    CognitiveVisionEngine,
    EvidenceEngine,
    FeatureExtractionEngine,
    ReasoningEngine,
)
from cognitive.events import EventBus
from core.logging_setup import get_logger

log = get_logger("cognitive.container")


class CognitiveContainer:
    """
    Wires independent engines. Replace any engine without touching the others.
    """

    def __init__(self, *, bus: EventBus | None = None) -> None:
        self.bus = bus or EventBus()
        self.vision = CognitiveVisionEngine(bus=self.bus)
        self.reconstruction = ChartReconstructionEngine(bus=self.bus)
        self.features = FeatureExtractionEngine(bus=self.bus)
        self.evidence = EvidenceEngine(bus=self.bus)
        self.reasoning = ReasoningEngine(bus=self.bus)
        self.risk = CognitiveRiskEngine(bus=self.bus)
        self.decision = CognitiveDecisionEngine(bus=self.bus)
        self.memory = CognitiveMemoryEngine(bus=self.bus)
        self.learning = CognitiveLearningEngine(bus=self.bus)
        log.info("CognitiveContainer ready")


@lru_cache(maxsize=1)
def get_cognitive_container() -> CognitiveContainer:
    return CognitiveContainer()


def reset_cognitive_container() -> None:
    get_cognitive_container.cache_clear()
