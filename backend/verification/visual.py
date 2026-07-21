"""
Build ChartVisualSnapshot from MarketModel / EngineBundle vision summaries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from verification.models import ChartVisualSnapshot


def from_market_model(market: Any) -> ChartVisualSnapshot:
    """Extract comparable fields from a cognitive MarketModel (no pixels)."""
    swings = getattr(market, "swing_points", None) or []
    highs = [s.price for s in swings if getattr(s, "kind", None) == "high"]
    lows = [s.price for s in swings if getattr(s, "kind", None) == "low"]
    candles = getattr(market, "candles", None) or []
    closes = [float(c.close) for c in candles if getattr(c, "close", None) is not None]
    trend_obj = getattr(market, "trend", None)
    trend = getattr(trend_obj, "direction", None) or "Unknown"
    return ChartVisualSnapshot(
        pair=str(getattr(market, "pair", "Unknown") or "Unknown"),
        timeframe=str(getattr(market, "timeframe", "Unknown") or "Unknown"),
        trend=str(trend),
        structure_label=str(getattr(market, "structure_label", "Unknown") or "Unknown"),
        recent_high=max(highs) if highs else (max(closes) if closes else None),
        recent_low=min(lows) if lows else (min(closes) if closes else None),
        swing_highs=highs[-5:],
        swing_lows=lows[-5:],
        candle_closes=closes[-20:],
        candle_count=len(candles),
        image_quality=float(getattr(market, "image_quality_score", 0.0) or 0.0),
        captured_at=datetime.now(timezone.utc),
        source="market_model",
    )


def from_vision_summary(
    *,
    pair: str,
    timeframe: str,
    summary: dict[str, Any],
) -> ChartVisualSnapshot:
    """Lightweight snapshot from EngineBundle.vision_summaries (unit tests / Brain)."""
    trend = str(summary.get("trend") or "Unknown")
    structure = str(summary.get("structure") or summary.get("structure_label") or "Unknown")
    closes = [float(x) for x in (summary.get("candle_closes") or [])]
    highs = [float(x) for x in (summary.get("swing_highs") or [])]
    lows = [float(x) for x in (summary.get("swing_lows") or [])]
    recent_high = summary.get("recent_high")
    recent_low = summary.get("recent_low")
    if recent_high is not None:
        recent_high = float(recent_high)
    elif highs:
        recent_high = max(highs)
    elif closes:
        recent_high = max(closes)
    if recent_low is not None:
        recent_low = float(recent_low)
    elif lows:
        recent_low = min(lows)
    elif closes:
        recent_low = min(closes)

    return ChartVisualSnapshot(
        pair=pair,
        timeframe=timeframe,
        trend=trend,
        structure_label=structure,
        recent_high=recent_high,
        recent_low=recent_low,
        swing_highs=highs[-5:],
        swing_lows=lows[-5:],
        candle_closes=closes[-20:],
        candle_count=int(summary.get("candle_count") or len(closes)),
        image_quality=float(summary.get("quality") or summary.get("image_quality") or 0.0),
        captured_at=None,
        source="vision_summary",
    )
