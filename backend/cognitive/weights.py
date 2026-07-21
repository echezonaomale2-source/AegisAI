"""Default evidence weights — Learning Engine adjusts these incrementally."""

from __future__ import annotations

# Base influence weights (not percentages). Learning multiplies reliability factors.
DEFAULT_FEATURE_WEIGHTS: dict[str, float] = {
    "trend": 15.0,
    "range": 8.0,
    "bos": 18.0,
    "choch": 16.0,
    "liquidity_sweep": 14.0,
    "equal_highs": 10.0,
    "equal_lows": 10.0,
    "liquidity": 8.0,
    "internal_liquidity": 9.0,
    "external_liquidity": 10.0,
    "bullish_order_block": 12.0,
    "bearish_order_block": 12.0,
    "bullish_fvg": 10.0,
    "bearish_fvg": 10.0,
    "demand_zone": 9.0,
    "supply_zone": 9.0,
    "discount": 8.0,
    "premium": 8.0,
    "impulse": 7.0,
    "impulse_move": 7.0,
    "pullback": 5.0,
    "retracement": 5.0,
    "rejection": 6.0,
    "mitigation": 6.0,
    "higher_high": 6.0,
    "higher_low": 6.0,
    "lower_high": 6.0,
    "lower_low": 6.0,
    "swing_high": 3.0,
    "swing_low": 3.0,
}

# Timeframe multipliers for evidence aggregation (top-down emphasis).
TF_MULTIPLIERS: dict[str, float] = {
    "4H": 1.30,
    "1H": 1.10,
    "15M": 0.95,
}

MIN_EVIDENCE_SCORE = 55.0
MIN_MARGIN = 12.0  # buy vs sell score gap required
MIN_CONFIDENCE = 70.0
