"""Evaluate declarative knowledge conditions and named validation rules."""

from __future__ import annotations

from typing import Any, Callable

from knowledge.models import Condition


def _resolve(context: dict[str, Any], field: str) -> Any:
    cur: Any = context
    for part in field.split("."):
        if cur is None:
            return None
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            cur = getattr(cur, part, None)
    return cur


def evaluate_condition(condition: Condition, context: dict[str, Any]) -> bool:
    actual = _resolve(context, condition.field)
    op = condition.op
    expected = condition.value

    if op == "exists":
        return actual is not None
    if op == "truthy":
        return bool(actual)
    if op == "falsy":
        return not bool(actual)
    if op == "eq":
        return actual == expected
    if op == "neq":
        return actual != expected
    if op == "gte":
        return actual is not None and actual >= expected
    if op == "lte":
        return actual is not None and actual <= expected
    if op == "gt":
        return actual is not None and actual > expected
    if op == "lt":
        return actual is not None and actual < expected
    if op == "in":
        return actual in (expected or [])
    return False


def describe_failure(condition: Condition, context: dict[str, Any]) -> str:
    actual = _resolve(context, condition.field)
    base = condition.description or f"{condition.field} {condition.op} {condition.value}"
    return f"{base} (actual={actual!r})"


def _trend_dir(context: dict[str, Any]) -> str:
    trend = context.get("trend") or {}
    if isinstance(trend, dict):
        return str(trend.get("direction") or "Unknown")
    return str(getattr(trend, "direction", "Unknown"))


_NAMED_RULES: dict[str, Callable[[dict[str, Any]], tuple[bool, str]]] = {
    "prefer_hh_hl": lambda ctx: (
        bool(ctx.get("has_higher_high") or ctx.get("has_higher_low")),
        "prefer HH/HL structure for bullish trend",
    ),
    "prefer_lh_ll": lambda ctx: (
        bool(ctx.get("has_lower_high") or ctx.get("has_lower_low")),
        "prefer LH/LL structure for bearish trend",
    ),
    "require_bullish_direction": lambda ctx: (
        _trend_dir(ctx) == "Bullish",
        "require bullish trend direction",
    ),
    "require_bearish_direction": lambda ctx: (
        _trend_dir(ctx) == "Bearish",
        "require bearish trend direction",
    ),
    "require_range_direction": lambda ctx: (
        _trend_dir(ctx) == "Range",
        "require ranging market",
    ),
    "require_directional_trend": lambda ctx: (
        _trend_dir(ctx) in {"Bullish", "Bearish"},
        "require directional (non-Unknown) trend",
    ),
    "require_usable_market": lambda ctx: (
        bool(ctx.get("market_usable")),
        "require usable market reconstruction",
    ),
    "require_swing_structure_or_label": lambda ctx: (
        bool(
            ctx.get("has_higher_high")
            or ctx.get("has_higher_low")
            or ctx.get("has_lower_high")
            or ctx.get("has_lower_low")
            or ctx.get("structure_label")
        ),
        "require swing structure or structure label",
    ),
    "require_swing_high_structure": lambda ctx: (
        bool(ctx.get("has_higher_high") or ctx.get("has_lower_high")),
        "require swing high structure",
    ),
    "require_swing_low_structure": lambda ctx: (
        bool(ctx.get("has_higher_low") or ctx.get("has_lower_low")),
        "require swing low structure",
    ),
    "require_bos_flag": lambda ctx: (bool(ctx.get("bos")), "require BOS flag"),
    "require_choch_flag": lambda ctx: (bool(ctx.get("choch")), "require CHOCH flag"),
    "require_bullish_ob": lambda ctx: (bool(ctx.get("has_bullish_ob")), "require bullish OB"),
    "require_bearish_ob": lambda ctx: (bool(ctx.get("has_bearish_ob")), "require bearish OB"),
    "require_bullish_fvg": lambda ctx: (bool(ctx.get("has_bullish_fvg")), "require bullish FVG"),
    "require_bearish_fvg": lambda ctx: (bool(ctx.get("has_bearish_fvg")), "require bearish FVG"),
    "require_liquidity_zone": lambda ctx: (bool(ctx.get("has_liquidity")), "require liquidity"),
    "require_internal_liquidity": lambda ctx: (
        bool(ctx.get("has_internal_liquidity")),
        "require internal liquidity",
    ),
    "require_external_liquidity": lambda ctx: (
        bool(ctx.get("has_external_liquidity")),
        "require external liquidity",
    ),
    "require_liquidity_sweep": lambda ctx: (
        bool(ctx.get("has_liquidity_sweep")),
        "require liquidity sweep",
    ),
    "require_supply": lambda ctx: (bool(ctx.get("has_supply")), "require supply zone"),
    "require_demand": lambda ctx: (bool(ctx.get("has_demand")), "require demand zone"),
    "require_premium": lambda ctx: (ctx.get("premium") == "Yes", "require premium"),
    "require_discount": lambda ctx: (ctx.get("discount") == "Yes", "require discount"),
    "require_impulse": lambda ctx: (bool(ctx.get("has_impulse")), "require impulse"),
    "require_retracement": lambda ctx: (bool(ctx.get("has_retracement")), "require retracement"),
    "require_mitigation": lambda ctx: (bool(ctx.get("has_mitigation")), "require mitigation"),
}


def evaluate_named_rule(rule: str, context: dict[str, Any]) -> tuple[bool, str, bool]:
    """
    Evaluate a catalog validation_rules string.

    Returns (passed, description, soft).
    soft=True means prefer_* — failure adds a note, does not invalidate.
    """
    soft = rule.startswith("prefer_")
    fn = _NAMED_RULES.get(rule)
    if fn is None:
        return True, f"unrecognized rule '{rule}' (ignored)", True
    ok, desc = fn(context)
    return ok, desc, soft
