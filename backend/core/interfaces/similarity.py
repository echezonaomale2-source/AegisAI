"""Similarity search interface."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class SimilarityEngineProtocol(Protocol):
    def find_similar(
        self,
        fingerprint_bits: list[int],
        *,
        direction: str | None = None,
        pair: str | None = None,
    ) -> Any:
        ...
