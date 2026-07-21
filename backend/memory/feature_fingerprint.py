"""Feature fingerprint builder for trade memory."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import TradeDecision

# Ordered feature keys — stable vector for similarity / indexing.
FEATURE_KEYS: list[str] = [
    "trend_alignment",
    "higher_highs",
    "higher_lows",
    "lower_highs",
    "lower_lows",
    "bos",
    "choch",
    "liquidity_sweep",
    "equal_highs",
    "equal_lows",
    "bullish_order_block",
    "bearish_order_block",
    "bullish_fvg",
    "bearish_fvg",
    "supply_zone",
    "demand_zone",
    "premium",
    "discount",
    "session_london",
    "session_new_york",
    "session_asian",
    "direction_buy",
    "direction_sell",
]


def _structure_flags(analysis: ChartAnalysis) -> dict[str, bool]:
    ms = (analysis.market_structure or "").lower()
    return {
        "higher_highs": "higher high" in ms,
        "higher_lows": "higher low" in ms,
        "lower_highs": "lower high" in ms,
        "lower_lows": "lower low" in ms,
    }


def _any_true(*flags: bool) -> bool:
    return any(flags)


def build_feature_map(decision: TradeDecision) -> dict[str, bool]:
    h4 = decision.analysis_4h
    h1 = decision.analysis_1h
    m15 = decision.analysis_15m

    s4 = _structure_flags(h4)
    s1 = _structure_flags(h1)
    s15 = _structure_flags(m15)

    sessions = set()
    for chart in (h4, h1, m15):
        sessions.update(chart.session_labels or [])

    trend_aligned = (
        decision.overall_bias == "BUY"
        and h4.trend == "Bullish"
        and h1.trend == "Bullish"
    ) or (
        decision.overall_bias == "SELL"
        and h4.trend == "Bearish"
        and h1.trend == "Bearish"
    )

    return {
        "trend_alignment": trend_aligned,
        "higher_highs": _any_true(s4["higher_highs"], s1["higher_highs"], s15["higher_highs"]),
        "higher_lows": _any_true(s4["higher_lows"], s1["higher_lows"], s15["higher_lows"]),
        "lower_highs": _any_true(s4["lower_highs"], s1["lower_highs"], s15["lower_highs"]),
        "lower_lows": _any_true(s4["lower_lows"], s1["lower_lows"], s15["lower_lows"]),
        "bos": _any_true(h4.bos, h1.bos, m15.bos),
        "choch": _any_true(h4.choch, h1.choch, m15.choch),
        "liquidity_sweep": _any_true(h4.liquidity_sweep, h1.liquidity_sweep, m15.liquidity_sweep),
        "equal_highs": _any_true(h4.equal_highs, h1.equal_highs, m15.equal_highs),
        "equal_lows": _any_true(h4.equal_lows, h1.equal_lows, m15.equal_lows),
        "bullish_order_block": _any_true(
            h4.bullish_order_block, h1.bullish_order_block, m15.bullish_order_block
        ),
        "bearish_order_block": _any_true(
            h4.bearish_order_block, h1.bearish_order_block, m15.bearish_order_block
        ),
        "bullish_fvg": _any_true(
            h4.fvg_type == "Bullish FVG",
            h1.fvg_type == "Bullish FVG",
            m15.fvg_type == "Bullish FVG",
        ),
        "bearish_fvg": _any_true(
            h4.fvg_type == "Bearish FVG",
            h1.fvg_type == "Bearish FVG",
            m15.fvg_type == "Bearish FVG",
        ),
        "supply_zone": _any_true(h4.supply_zone, h1.supply_zone, m15.supply_zone),
        "demand_zone": _any_true(h4.demand_zone, h1.demand_zone, m15.demand_zone),
        "premium": _any_true(h4.premium == "Yes", h1.premium == "Yes", m15.premium == "Yes"),
        "discount": _any_true(h4.discount == "Yes", h1.discount == "Yes", m15.discount == "Yes"),
        "session_london": "London" in sessions,
        "session_new_york": "New York" in sessions,
        "session_asian": "Asian" in sessions,
        "direction_buy": decision.overall_bias == "BUY",
        "direction_sell": decision.overall_bias == "SELL",
    }


def features_to_bits(features: dict[str, bool]) -> str:
    return "".join("1" if features.get(key, False) else "0" for key in FEATURE_KEYS)


def bits_to_features(bits: str) -> dict[str, bool]:
    values = list(bits.ljust(len(FEATURE_KEYS), "0"))
    return {key: values[i] == "1" for i, key in enumerate(FEATURE_KEYS)}


def fingerprint_hash(bits: str) -> str:
    return hashlib.sha1(bits.encode("utf-8")).hexdigest()


def build_fingerprint(decision: TradeDecision) -> dict[str, Any]:
    features = build_feature_map(decision)
    bits = features_to_bits(features)
    return {
        "features": features,
        "bits": bits,
        "hash": fingerprint_hash(bits),
        "active_features": [k for k, v in features.items() if v],
    }


def fingerprint_json(fingerprint: dict[str, Any]) -> str:
    return json.dumps(fingerprint["features"], sort_keys=True)
