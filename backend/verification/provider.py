"""
Pluggable market-data provider interface.

Providers are replaceable. The Decision Engine / AI Brain never depend on a
specific broker or vendor.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from verification.models import MarketDataSnapshot, OHLCCandle


@runtime_checkable
class MarketDataProvider(Protocol):
    """
    Fetch optional OHLC data for verification.

    Implementations must never raise for routine unavailability —
    return None instead so screenshot analysis continues.
    """

    @property
    def name(self) -> str: ...

    def available(self) -> bool:
        """True when the provider can attempt a fetch."""
        ...

    def fetch(
        self,
        pair: str,
        timeframe: str,
        *,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> MarketDataSnapshot | None:
        """
        Return a snapshot or None if data is unavailable.

        Network failures should return None (or raise only if the caller
        explicitly wants errors — VerificationEngine catches exceptions).
        """
        ...


class NullMarketDataProvider:
    """Default provider — always unavailable. Screenshot-only path."""

    @property
    def name(self) -> str:
        return "null"

    def available(self) -> bool:
        return False

    def fetch(
        self,
        pair: str,
        timeframe: str,
        *,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> MarketDataSnapshot | None:
        return None


class InMemoryMarketDataProvider:
    """
    Deterministic in-memory provider for tests and offline demos.

    Keyed by (PAIR.upper(), TIMEFRAME.upper()).
    """

    def __init__(
        self,
        snapshots: dict[tuple[str, str], MarketDataSnapshot] | None = None,
        *,
        fail_network: bool = False,
    ) -> None:
        self._snapshots = snapshots or {}
        self._fail_network = fail_network

    @property
    def name(self) -> str:
        return "in_memory"

    def available(self) -> bool:
        return not self._fail_network and bool(self._snapshots)

    def put(self, snapshot: MarketDataSnapshot) -> None:
        key = (snapshot.pair.upper(), snapshot.timeframe.upper())
        self._snapshots[key] = snapshot

    def fetch(
        self,
        pair: str,
        timeframe: str,
        *,
        end_time: datetime | None = None,
        limit: int = 100,
    ) -> MarketDataSnapshot | None:
        if self._fail_network:
            raise ConnectionError("Simulated network failure")
        key = (pair.upper(), timeframe.upper())
        snap = self._snapshots.get(key)
        if snap is None:
            return None
        candles = snap.candles[-limit:] if limit else snap.candles
        return snap.model_copy(update={"candles": list(candles)})


def make_ohlc_series(
    closes: list[float],
    *,
    start: float | None = None,
) -> list[OHLCCandle]:
    """Helper to build simple OHLC series from close prices (tests / fixtures)."""
    out: list[OHLCCandle] = []
    prev = start if start is not None else (closes[0] if closes else 0.0)
    for i, close in enumerate(closes):
        high = max(prev, close) * 1.001
        low = min(prev, close) * 0.999
        out.append(
            OHLCCandle(
                open=prev,
                high=high,
                low=low,
                close=close,
                index=i,
            )
        )
        prev = close
    return out
