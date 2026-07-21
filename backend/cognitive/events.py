"""Lightweight event bus for loose coupling between engines."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable

from core.logging_setup import get_logger

log = get_logger("cognitive.events")

Listener = Callable[[str, dict[str, Any]], None]


@dataclass
class EventBus:
    """Simple synchronous pub/sub — engines emit; observers subscribe."""

    _listeners: dict[str, list[Listener]] = field(default_factory=lambda: defaultdict(list))

    def subscribe(self, event: str, listener: Listener) -> None:
        self._listeners[event].append(listener)

    def publish(self, event: str, payload: dict[str, Any] | None = None) -> None:
        data = payload or {}
        log.debug("event=%s keys=%s", event, list(data.keys()))
        for listener in self._listeners.get(event, []):
            try:
                listener(event, data)
            except Exception as exc:  # noqa: BLE001
                log.warning("listener failed event=%s: %s", event, exc)

    def clear(self) -> None:
        self._listeners.clear()


# Shared event names
EVT_VISION_DONE = "vision.done"
EVT_MARKET_REBUILT = "market.rebuilt"
EVT_FEATURES_EXTRACTED = "features.extracted"
EVT_EVIDENCE_BUILT = "evidence.built"
EVT_REASONING_DONE = "reasoning.done"
EVT_DECISION_MADE = "decision.made"
EVT_RISK_ASSESSED = "risk.assessed"
EVT_MEMORY_STORED = "memory.stored"
EVT_LEARNING_UPDATED = "learning.updated"
