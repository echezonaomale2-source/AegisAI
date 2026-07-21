"""Knowledge catalog v1.0 — authoritative SMC concept definitions."""

from __future__ import annotations

from knowledge.models import (
    ConceptDefinition,
    ConceptExample,
    Condition,
    ConfidenceGuidelines,
    Relationship,
)

VERSION = "1.0"


def _c(
    field: str,
    op: str,
    value=None,
    description: str = "",
) -> Condition:
    return Condition(field=field, op=op, value=value, description=description)  # type: ignore[arg-type]


def _ex(title: str, valid: bool, context: dict, notes: str = "") -> ConceptExample:
    return ConceptExample(title=title, valid=valid, context=context, notes=notes)


def build_relationships() -> list[Relationship]:
    return [
        Relationship(
            source="bos",
            target="trend",
            relation="strengthens",
            description="BOS may strengthen trend continuation when aligned with HTF bias.",
            strengthens_trade=False,
        ),
        Relationship(
            source="choch",
            target="trend",
            relation="may_reverse",
            description="CHOCH may indicate a potential reversal — not a standalone entry.",
            strengthens_trade=False,
        ),
        Relationship(
            source="liquidity_sweep",
            target="bullish_order_block",
            relation="may_strengthen",
            description="Liquidity sweep may strengthen a subsequent Order Block reaction.",
            strengthens_trade=False,
        ),
        Relationship(
            source="liquidity_sweep",
            target="bearish_order_block",
            relation="may_strengthen",
            description="Liquidity sweep may strengthen a subsequent Order Block reaction.",
            strengthens_trade=False,
        ),
        Relationship(
            source="bullish_order_block",
            target="bullish_fvg",
            relation="may_reinforce",
            description="Order Blocks and FVGs may reinforce each other when overlapping in direction.",
            strengthens_trade=False,
        ),
        Relationship(
            source="bearish_order_block",
            target="bearish_fvg",
            relation="may_reinforce",
            description="Order Blocks and FVGs may reinforce each other when overlapping in direction.",
            strengthens_trade=False,
        ),
        Relationship(
            source="demand_zone",
            target="discount",
            relation="aligned_with",
            description="Demand in discount is stronger confluence than demand in premium.",
            strengthens_trade=False,
        ),
        Relationship(
            source="supply_zone",
            target="premium",
            relation="aligned_with",
            description="Supply in premium is stronger confluence than supply in discount.",
            strengthens_trade=False,
        ),
        Relationship(
            source="impulse_move",
            target="retracement",
            relation="followed_by",
            description="Impulse moves are often followed by retracements; retracement alone is not entry.",
            strengthens_trade=False,
        ),
        Relationship(
            source="higher_high",
            target="bullish_trend",
            relation="defines",
            description="Series of HH/HL defines a bullish trend structure.",
            strengthens_trade=False,
        ),
        Relationship(
            source="lower_low",
            target="bearish_trend",
            relation="defines",
            description="Series of LL/LH defines a bearish trend structure.",
            strengthens_trade=False,
        ),
        Relationship(
            source="mitigation",
            target="bullish_order_block",
            relation="consumes",
            description="Mitigation may reduce remaining Order Block validity.",
            strengthens_trade=False,
        ),
        Relationship(
            source="mitigation",
            target="bearish_order_block",
            relation="consumes",
            description="Mitigation may reduce remaining Order Block validity.",
            strengthens_trade=False,
        ),
    ]


def build_concepts() -> list[ConceptDefinition]:
    g = ConfidenceGuidelines
    concepts: list[ConceptDefinition] = [
        ConceptDefinition(
            id="trend",
            name="Trend",
            definition=(
                "Directional market behavior defined by successive swing structure. "
                "Trend is Unknown when swings are insufficient or conflicting."
            ),
            validation_rules=["require_usable_market", "require_swing_structure_or_label"],
            required_conditions=[
                _c("market_usable", "truthy", description="Market model must be usable"),
                _c("trend.direction", "in", ["Bullish", "Bearish", "Range"], description="Direction must be classified"),
            ],
            invalid_conditions=[
                _c("trend.direction", "eq", "Unknown", description="Unknown trend is not a detection"),
            ],
            relationships=["higher_high->bullish_trend", "lower_low->bearish_trend"],
            examples=[
                _ex("Clear bullish label", True, {"market_usable": True, "trend": {"direction": "Bullish", "confidence": 80}}),
                _ex("Unknown trend", False, {"market_usable": True, "trend": {"direction": "Unknown", "confidence": 0}}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80, notes="Use swing clarity for confidence."),
            version=VERSION,
            feature_types=["trend", "range"],
            tags=["structure"],
        ),
        ConceptDefinition(
            id="bullish_trend",
            name="Bullish Trend",
            definition="Market making higher highs and higher lows, with bullish structural progression.",
            validation_rules=["require_bullish_direction", "prefer_hh_hl"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("trend.direction", "eq", "Bullish"),
            ],
            invalid_conditions=[
                _c("trend.direction", "eq", "Bearish"),
                _c("trend.direction", "eq", "Unknown"),
            ],
            relationships=["bos->trend"],
            examples=[
                _ex("Bullish trend", True, {"market_usable": True, "trend": {"direction": "Bullish", "confidence": 85}}),
                _ex("Bearish labeled", False, {"market_usable": True, "trend": {"direction": "Bearish", "confidence": 85}}),
            ],
            confidence_guidelines=g(min_detect=55, high_confidence=85),
            version=VERSION,
            feature_types=["trend"],
            tags=["structure", "bullish"],
        ),
        ConceptDefinition(
            id="bearish_trend",
            name="Bearish Trend",
            definition="Market making lower highs and lower lows, with bearish structural progression.",
            validation_rules=["require_bearish_direction"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("trend.direction", "eq", "Bearish"),
            ],
            invalid_conditions=[
                _c("trend.direction", "eq", "Bullish"),
                _c("trend.direction", "eq", "Unknown"),
            ],
            relationships=["choch->trend"],
            examples=[
                _ex("Bearish trend", True, {"market_usable": True, "trend": {"direction": "Bearish", "confidence": 85}}),
                _ex("Range labeled", False, {"market_usable": True, "trend": {"direction": "Range", "confidence": 60}}),
            ],
            confidence_guidelines=g(min_detect=55, high_confidence=85),
            version=VERSION,
            feature_types=["trend"],
            tags=["structure", "bearish"],
        ),
        ConceptDefinition(
            id="range",
            name="Range",
            definition="Sideways market lacking clear HH/HL or LH/LL progression; equal swings dominate.",
            validation_rules=["require_range_direction"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("trend.direction", "eq", "Range"),
            ],
            invalid_conditions=[
                _c("trend.direction", "in", ["Bullish", "Bearish"]),
            ],
            relationships=[],
            examples=[
                _ex("Range", True, {"market_usable": True, "trend": {"direction": "Range", "confidence": 70}}),
                _ex("Bullish", False, {"market_usable": True, "trend": {"direction": "Bullish", "confidence": 80}}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=75),
            version=VERSION,
            feature_types=["range"],
            tags=["structure"],
        ),
        ConceptDefinition(
            id="higher_high",
            name="Higher High",
            definition="A swing high that exceeds the previous significant swing high.",
            validation_rules=["require_swing_high_structure"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_higher_high", "truthy"),
            ],
            invalid_conditions=[
                _c("candle_count", "lt", 5),
            ],
            relationships=["higher_high->bullish_trend"],
            examples=[
                _ex("HH present", True, {"market_usable": True, "has_higher_high": True, "candle_count": 12}),
                _ex("No HH", False, {"market_usable": True, "has_higher_high": False, "candle_count": 12}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["higher_high", "swing_high"],
            tags=["structure", "bullish"],
        ),
        ConceptDefinition(
            id="higher_low",
            name="Higher Low",
            definition="A swing low that is higher than the previous significant swing low.",
            validation_rules=["require_swing_low_structure"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_higher_low", "truthy"),
            ],
            invalid_conditions=[_c("candle_count", "lt", 5)],
            relationships=["higher_high->bullish_trend"],
            examples=[
                _ex("HL present", True, {"market_usable": True, "has_higher_low": True, "candle_count": 12}),
                _ex("No HL", False, {"market_usable": True, "has_higher_low": False, "candle_count": 12}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["higher_low", "swing_low"],
            tags=["structure", "bullish"],
        ),
        ConceptDefinition(
            id="lower_high",
            name="Lower High",
            definition="A swing high that is lower than the previous significant swing high.",
            validation_rules=["require_swing_high_structure"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_lower_high", "truthy"),
            ],
            invalid_conditions=[_c("candle_count", "lt", 5)],
            relationships=["lower_low->bearish_trend"],
            examples=[
                _ex("LH present", True, {"market_usable": True, "has_lower_high": True, "candle_count": 12}),
                _ex("No LH", False, {"market_usable": True, "has_lower_high": False, "candle_count": 12}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["lower_high"],
            tags=["structure", "bearish"],
        ),
        ConceptDefinition(
            id="lower_low",
            name="Lower Low",
            definition="A swing low that is lower than the previous significant swing low.",
            validation_rules=["require_swing_low_structure"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_lower_low", "truthy"),
            ],
            invalid_conditions=[_c("candle_count", "lt", 5)],
            relationships=["lower_low->bearish_trend"],
            examples=[
                _ex("LL present", True, {"market_usable": True, "has_lower_low": True, "candle_count": 12}),
                _ex("No LL", False, {"market_usable": True, "has_lower_low": False, "candle_count": 12}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["lower_low"],
            tags=["structure", "bearish"],
        ),
        ConceptDefinition(
            id="bos",
            name="Break of Structure (BOS)",
            definition=(
                "Price breaks a significant structural point in the direction of the prevailing trend, "
                "signaling continuation potential — not an automatic entry."
            ),
            validation_rules=["require_bos_flag", "require_directional_trend"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("bos", "truthy"),
                _c("trend.direction", "in", ["Bullish", "Bearish"]),
            ],
            invalid_conditions=[
                _c("trend.direction", "eq", "Unknown"),
                _c("bos", "falsy"),
            ],
            relationships=["bos->trend"],
            examples=[
                _ex(
                    "BOS with bullish trend",
                    True,
                    {"market_usable": True, "bos": True, "trend": {"direction": "Bullish", "confidence": 80}},
                ),
                _ex(
                    "BOS flag without trend",
                    False,
                    {"market_usable": True, "bos": True, "trend": {"direction": "Unknown", "confidence": 0}},
                ),
            ],
            confidence_guidelines=g(min_detect=60, high_confidence=88, notes="BOS without clear trend → Unknown."),
            version=VERSION,
            feature_types=["bos"],
            tags=["structure"],
        ),
        ConceptDefinition(
            id="choch",
            name="Change of Character (CHOCH)",
            definition=(
                "A structural break against the prior trend character that may indicate a potential reversal. "
                "CHOCH alone does not justify a trade."
            ),
            validation_rules=["require_choch_flag"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("choch", "truthy"),
            ],
            invalid_conditions=[
                _c("choch", "falsy"),
                _c("candle_count", "lt", 5),
            ],
            relationships=["choch->trend"],
            examples=[
                _ex("CHOCH present", True, {"market_usable": True, "choch": True, "candle_count": 20}),
                _ex("No CHOCH", False, {"market_usable": True, "choch": False, "candle_count": 20}),
            ],
            confidence_guidelines=g(min_detect=60, high_confidence=85),
            version=VERSION,
            feature_types=["choch"],
            tags=["structure", "reversal"],
        ),
        ConceptDefinition(
            id="bullish_order_block",
            name="Bullish Order Block",
            definition=(
                "The last bearish (or opposing) candle zone before a strong bullish displacement, "
                "acting as potential demand. Must not be fully mitigated without remaining validity."
            ),
            validation_rules=["require_bullish_ob"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_bullish_ob", "truthy"),
            ],
            invalid_conditions=[
                _c("has_bullish_ob", "falsy"),
            ],
            relationships=["bullish_order_block->bullish_fvg", "liquidity_sweep->bullish_order_block"],
            examples=[
                _ex("Bullish OB", True, {"market_usable": True, "has_bullish_ob": True}),
                _ex("No bullish OB", False, {"market_usable": True, "has_bullish_ob": False}),
            ],
            confidence_guidelines=g(min_detect=55, high_confidence=85),
            version=VERSION,
            feature_types=["bullish_order_block"],
            tags=["order_block", "bullish"],
        ),
        ConceptDefinition(
            id="bearish_order_block",
            name="Bearish Order Block",
            definition=(
                "The last bullish (or opposing) candle zone before a strong bearish displacement, "
                "acting as potential supply."
            ),
            validation_rules=["require_bearish_ob"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_bearish_ob", "truthy"),
            ],
            invalid_conditions=[_c("has_bearish_ob", "falsy")],
            relationships=["bearish_order_block->bearish_fvg", "liquidity_sweep->bearish_order_block"],
            examples=[
                _ex("Bearish OB", True, {"market_usable": True, "has_bearish_ob": True}),
                _ex("No bearish OB", False, {"market_usable": True, "has_bearish_ob": False}),
            ],
            confidence_guidelines=g(min_detect=55, high_confidence=85),
            version=VERSION,
            feature_types=["bearish_order_block"],
            tags=["order_block", "bearish"],
        ),
        ConceptDefinition(
            id="bullish_fvg",
            name="Bullish Fair Value Gap",
            definition=(
                "An imbalance where a bullish displacement leaves a gap between candle wicks/bodies "
                "that may act as support on revisit. Incomplete detection → Unknown."
            ),
            validation_rules=["require_bullish_fvg"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_bullish_fvg", "truthy"),
            ],
            invalid_conditions=[_c("has_bullish_fvg", "falsy")],
            relationships=["bullish_order_block->bullish_fvg"],
            examples=[
                _ex("Bullish FVG", True, {"market_usable": True, "has_bullish_fvg": True}),
                _ex("No FVG", False, {"market_usable": True, "has_bullish_fvg": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["bullish_fvg"],
            tags=["fvg", "bullish"],
        ),
        ConceptDefinition(
            id="bearish_fvg",
            name="Bearish Fair Value Gap",
            definition=(
                "An imbalance where a bearish displacement leaves a gap that may act as resistance on revisit."
            ),
            validation_rules=["require_bearish_fvg"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_bearish_fvg", "truthy"),
            ],
            invalid_conditions=[_c("has_bearish_fvg", "falsy")],
            relationships=["bearish_order_block->bearish_fvg"],
            examples=[
                _ex("Bearish FVG", True, {"market_usable": True, "has_bearish_fvg": True}),
                _ex("No FVG", False, {"market_usable": True, "has_bearish_fvg": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["bearish_fvg"],
            tags=["fvg", "bearish"],
        ),
        ConceptDefinition(
            id="liquidity",
            name="Liquidity",
            definition="Pools of resting orders above highs or below lows (equal highs/lows, session highs/lows).",
            validation_rules=["require_liquidity_zone"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_liquidity", "truthy"),
            ],
            invalid_conditions=[_c("has_liquidity", "falsy")],
            relationships=[],
            examples=[
                _ex("Liquidity present", True, {"market_usable": True, "has_liquidity": True}),
                _ex("No liquidity", False, {"market_usable": True, "has_liquidity": False}),
            ],
            confidence_guidelines=g(min_detect=45, high_confidence=80),
            version=VERSION,
            feature_types=["liquidity", "equal_highs", "equal_lows"],
            tags=["liquidity"],
        ),
        ConceptDefinition(
            id="internal_liquidity",
            name="Internal Liquidity",
            definition="Liquidity within the current dealing range (internal highs/lows), not the extremes.",
            validation_rules=["require_internal_liquidity"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_internal_liquidity", "truthy"),
            ],
            invalid_conditions=[_c("has_internal_liquidity", "falsy")],
            relationships=[],
            examples=[
                _ex("Internal liq", True, {"market_usable": True, "has_internal_liquidity": True}),
                _ex("None", False, {"market_usable": True, "has_internal_liquidity": False}),
            ],
            confidence_guidelines=g(min_detect=45, high_confidence=75),
            version=VERSION,
            feature_types=["internal_liquidity"],
            tags=["liquidity"],
        ),
        ConceptDefinition(
            id="external_liquidity",
            name="External Liquidity",
            definition="Liquidity beyond the current dealing range extremes (external highs/lows).",
            validation_rules=["require_external_liquidity"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_external_liquidity", "truthy"),
            ],
            invalid_conditions=[_c("has_external_liquidity", "falsy")],
            relationships=[],
            examples=[
                _ex("External liq", True, {"market_usable": True, "has_external_liquidity": True}),
                _ex("None", False, {"market_usable": True, "has_external_liquidity": False}),
            ],
            confidence_guidelines=g(min_detect=45, high_confidence=75),
            version=VERSION,
            feature_types=["external_liquidity"],
            tags=["liquidity"],
        ),
        ConceptDefinition(
            id="liquidity_sweep",
            name="Liquidity Sweep",
            definition=(
                "Price briefly takes liquidity beyond a high/low then reverses, often preceding displacement. "
                "Sweep alone is not an entry signal."
            ),
            validation_rules=["require_liquidity_sweep"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_liquidity_sweep", "truthy"),
            ],
            invalid_conditions=[_c("has_liquidity_sweep", "falsy")],
            relationships=[
                "liquidity_sweep->bullish_order_block",
                "liquidity_sweep->bearish_order_block",
            ],
            examples=[
                _ex("Sweep", True, {"market_usable": True, "has_liquidity_sweep": True}),
                _ex("No sweep", False, {"market_usable": True, "has_liquidity_sweep": False}),
            ],
            confidence_guidelines=g(min_detect=55, high_confidence=88),
            version=VERSION,
            feature_types=["liquidity_sweep"],
            tags=["liquidity"],
        ),
        ConceptDefinition(
            id="supply_zone",
            name="Supply Zone",
            definition="A price area where sell-side interest previously caused bearish displacement.",
            validation_rules=["require_supply"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_supply", "truthy"),
            ],
            invalid_conditions=[_c("has_supply", "falsy")],
            relationships=["supply_zone->premium"],
            examples=[
                _ex("Supply", True, {"market_usable": True, "has_supply": True}),
                _ex("No supply", False, {"market_usable": True, "has_supply": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["supply_zone"],
            tags=["zones", "bearish"],
        ),
        ConceptDefinition(
            id="demand_zone",
            name="Demand Zone",
            definition="A price area where buy-side interest previously caused bullish displacement.",
            validation_rules=["require_demand"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_demand", "truthy"),
            ],
            invalid_conditions=[_c("has_demand", "falsy")],
            relationships=["demand_zone->discount"],
            examples=[
                _ex("Demand", True, {"market_usable": True, "has_demand": True}),
                _ex("No demand", False, {"market_usable": True, "has_demand": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["demand_zone"],
            tags=["zones", "bullish"],
        ),
        ConceptDefinition(
            id="premium",
            name="Premium",
            definition="Price trading in the upper portion of the dealing range (expensive relative to equilibrium).",
            validation_rules=["require_premium"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("premium", "eq", "Yes"),
            ],
            invalid_conditions=[
                _c("premium", "eq", "Unknown"),
                _c("discount", "eq", "Yes"),
            ],
            relationships=["supply_zone->premium"],
            examples=[
                _ex("Premium", True, {"market_usable": True, "premium": "Yes", "discount": "No"}),
                _ex("Unknown premium", False, {"market_usable": True, "premium": "Unknown", "discount": "Unknown"}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=75),
            version=VERSION,
            feature_types=["premium"],
            tags=["pricing"],
        ),
        ConceptDefinition(
            id="discount",
            name="Discount",
            definition="Price trading in the lower portion of the dealing range (cheap relative to equilibrium).",
            validation_rules=["require_discount"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("discount", "eq", "Yes"),
            ],
            invalid_conditions=[
                _c("discount", "eq", "Unknown"),
                _c("premium", "eq", "Yes"),
            ],
            relationships=["demand_zone->discount"],
            examples=[
                _ex("Discount", True, {"market_usable": True, "discount": "Yes", "premium": "No"}),
                _ex("Unknown discount", False, {"market_usable": True, "discount": "Unknown", "premium": "Unknown"}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=75),
            version=VERSION,
            feature_types=["discount"],
            tags=["pricing"],
        ),
        ConceptDefinition(
            id="impulse_move",
            name="Impulse Move",
            definition="A strong directional displacement candle sequence showing institutional intent.",
            validation_rules=["require_impulse"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_impulse", "truthy"),
            ],
            invalid_conditions=[_c("has_impulse", "falsy")],
            relationships=["impulse_move->retracement"],
            examples=[
                _ex("Impulse", True, {"market_usable": True, "has_impulse": True}),
                _ex("No impulse", False, {"market_usable": True, "has_impulse": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["impulse"],
            tags=["structure"],
        ),
        ConceptDefinition(
            id="retracement",
            name="Retracement",
            definition="A pullback against the recent impulse that may offer continuation entries — not a reversal by itself.",
            validation_rules=["require_retracement"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_retracement", "truthy"),
            ],
            invalid_conditions=[_c("has_retracement", "falsy")],
            relationships=["impulse_move->retracement"],
            examples=[
                _ex("Retracement", True, {"market_usable": True, "has_retracement": True}),
                _ex("No retracement", False, {"market_usable": True, "has_retracement": False}),
            ],
            confidence_guidelines=g(min_detect=45, high_confidence=75),
            version=VERSION,
            feature_types=["pullback"],
            tags=["structure"],
        ),
        ConceptDefinition(
            id="mitigation",
            name="Mitigation",
            definition=(
                "Price returning into a prior Order Block / imbalance to fill or reduce unmitigated orders. "
                "Full mitigation may invalidate remaining block usefulness."
            ),
            validation_rules=["require_mitigation"],
            required_conditions=[
                _c("market_usable", "truthy"),
                _c("has_mitigation", "truthy"),
            ],
            invalid_conditions=[_c("has_mitigation", "falsy")],
            relationships=["mitigation->bullish_order_block"],
            examples=[
                _ex("Mitigation", True, {"market_usable": True, "has_mitigation": True}),
                _ex("No mitigation", False, {"market_usable": True, "has_mitigation": False}),
            ],
            confidence_guidelines=g(min_detect=50, high_confidence=80),
            version=VERSION,
            feature_types=["mitigation"],
            tags=["order_block"],
        ),
    ]
    return concepts
