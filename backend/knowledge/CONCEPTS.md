# SMC Concepts — Knowledge v1.0

Authoritative definitions used by the Knowledge Engine.

## Trend

- **ID:** trend
- **Version:** 1.0
- **Definition:** Directional market behavior defined by successive swing structure. Trend is Unknown when swings are insufficient or conflicting.
- **Validation rules:** require_usable_market, require_swing_structure_or_label
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** trend, range
- **Confidence:** min detect 50.0%, high 80.0%

## Bullish Trend

- **ID:** bullish_trend
- **Version:** 1.0
- **Definition:** Market making higher highs and higher lows, with bullish structural progression.
- **Validation rules:** require_bullish_direction, prefer_hh_hl
- **Required:** 2 conditions
- **Invalid when:** 2 conditions
- **Feature types:** trend
- **Confidence:** min detect 55.0%, high 85.0%

## Bearish Trend

- **ID:** bearish_trend
- **Version:** 1.0
- **Definition:** Market making lower highs and lower lows, with bearish structural progression.
- **Validation rules:** require_bearish_direction
- **Required:** 2 conditions
- **Invalid when:** 2 conditions
- **Feature types:** trend
- **Confidence:** min detect 55.0%, high 85.0%

## Range

- **ID:** range
- **Version:** 1.0
- **Definition:** Sideways market lacking clear HH/HL or LH/LL progression; equal swings dominate.
- **Validation rules:** require_range_direction
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** range
- **Confidence:** min detect 50.0%, high 75.0%

## Higher High

- **ID:** higher_high
- **Version:** 1.0
- **Definition:** A swing high that exceeds the previous significant swing high.
- **Validation rules:** require_swing_high_structure
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** higher_high, swing_high
- **Confidence:** min detect 50.0%, high 80.0%

## Higher Low

- **ID:** higher_low
- **Version:** 1.0
- **Definition:** A swing low that is higher than the previous significant swing low.
- **Validation rules:** require_swing_low_structure
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** higher_low, swing_low
- **Confidence:** min detect 50.0%, high 80.0%

## Lower High

- **ID:** lower_high
- **Version:** 1.0
- **Definition:** A swing high that is lower than the previous significant swing high.
- **Validation rules:** require_swing_high_structure
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** lower_high
- **Confidence:** min detect 50.0%, high 80.0%

## Lower Low

- **ID:** lower_low
- **Version:** 1.0
- **Definition:** A swing low that is lower than the previous significant swing low.
- **Validation rules:** require_swing_low_structure
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** lower_low
- **Confidence:** min detect 50.0%, high 80.0%

## Break of Structure (BOS)

- **ID:** bos
- **Version:** 1.0
- **Definition:** Price breaks a significant structural point in the direction of the prevailing trend, signaling continuation potential — not an automatic entry.
- **Validation rules:** require_bos_flag, require_directional_trend
- **Required:** 3 conditions
- **Invalid when:** 2 conditions
- **Feature types:** bos
- **Confidence:** min detect 60.0%, high 88.0%

## Change of Character (CHOCH)

- **ID:** choch
- **Version:** 1.0
- **Definition:** A structural break against the prior trend character that may indicate a potential reversal. CHOCH alone does not justify a trade.
- **Validation rules:** require_choch_flag
- **Required:** 2 conditions
- **Invalid when:** 2 conditions
- **Feature types:** choch
- **Confidence:** min detect 60.0%, high 85.0%

## Bullish Order Block

- **ID:** bullish_order_block
- **Version:** 1.0
- **Definition:** The last bearish (or opposing) candle zone before a strong bullish displacement, acting as potential demand. Must not be fully mitigated without remaining validity.
- **Validation rules:** require_bullish_ob
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** bullish_order_block
- **Confidence:** min detect 55.0%, high 85.0%

## Bearish Order Block

- **ID:** bearish_order_block
- **Version:** 1.0
- **Definition:** The last bullish (or opposing) candle zone before a strong bearish displacement, acting as potential supply.
- **Validation rules:** require_bearish_ob
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** bearish_order_block
- **Confidence:** min detect 55.0%, high 85.0%

## Bullish Fair Value Gap

- **ID:** bullish_fvg
- **Version:** 1.0
- **Definition:** An imbalance where a bullish displacement leaves a gap between candle wicks/bodies that may act as support on revisit. Incomplete detection → Unknown.
- **Validation rules:** require_bullish_fvg
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** bullish_fvg
- **Confidence:** min detect 50.0%, high 80.0%

## Bearish Fair Value Gap

- **ID:** bearish_fvg
- **Version:** 1.0
- **Definition:** An imbalance where a bearish displacement leaves a gap that may act as resistance on revisit.
- **Validation rules:** require_bearish_fvg
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** bearish_fvg
- **Confidence:** min detect 50.0%, high 80.0%

## Liquidity

- **ID:** liquidity
- **Version:** 1.0
- **Definition:** Pools of resting orders above highs or below lows (equal highs/lows, session highs/lows).
- **Validation rules:** require_liquidity_zone
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** liquidity, equal_highs, equal_lows
- **Confidence:** min detect 45.0%, high 80.0%

## Internal Liquidity

- **ID:** internal_liquidity
- **Version:** 1.0
- **Definition:** Liquidity within the current dealing range (internal highs/lows), not the extremes.
- **Validation rules:** require_internal_liquidity
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** liquidity
- **Confidence:** min detect 45.0%, high 75.0%

## External Liquidity

- **ID:** external_liquidity
- **Version:** 1.0
- **Definition:** Liquidity beyond the current dealing range extremes (external highs/lows).
- **Validation rules:** require_external_liquidity
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** liquidity
- **Confidence:** min detect 45.0%, high 75.0%

## Liquidity Sweep

- **ID:** liquidity_sweep
- **Version:** 1.0
- **Definition:** Price briefly takes liquidity beyond a high/low then reverses, often preceding displacement. Sweep alone is not an entry signal.
- **Validation rules:** require_liquidity_sweep
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** liquidity_sweep
- **Confidence:** min detect 55.0%, high 88.0%

## Supply Zone

- **ID:** supply_zone
- **Version:** 1.0
- **Definition:** A price area where sell-side interest previously caused bearish displacement.
- **Validation rules:** require_supply
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** supply_zone
- **Confidence:** min detect 50.0%, high 80.0%

## Demand Zone

- **ID:** demand_zone
- **Version:** 1.0
- **Definition:** A price area where buy-side interest previously caused bullish displacement.
- **Validation rules:** require_demand
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** demand_zone
- **Confidence:** min detect 50.0%, high 80.0%

## Premium

- **ID:** premium
- **Version:** 1.0
- **Definition:** Price trading in the upper portion of the dealing range (expensive relative to equilibrium).
- **Validation rules:** require_premium
- **Required:** 2 conditions
- **Invalid when:** 2 conditions
- **Feature types:** premium
- **Confidence:** min detect 50.0%, high 75.0%

## Discount

- **ID:** discount
- **Version:** 1.0
- **Definition:** Price trading in the lower portion of the dealing range (cheap relative to equilibrium).
- **Validation rules:** require_discount
- **Required:** 2 conditions
- **Invalid when:** 2 conditions
- **Feature types:** discount
- **Confidence:** min detect 50.0%, high 75.0%

## Impulse Move

- **ID:** impulse_move
- **Version:** 1.0
- **Definition:** A strong directional displacement candle sequence showing institutional intent.
- **Validation rules:** require_impulse
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** impulse
- **Confidence:** min detect 50.0%, high 80.0%

## Retracement

- **ID:** retracement
- **Version:** 1.0
- **Definition:** A pullback against the recent impulse that may offer continuation entries — not a reversal by itself.
- **Validation rules:** require_retracement
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** pullback
- **Confidence:** min detect 45.0%, high 75.0%

## Mitigation

- **ID:** mitigation
- **Version:** 1.0
- **Definition:** Price returning into a prior Order Block / imbalance to fill or reduce unmitigated orders. Full mitigation may invalidate remaining block usefulness.
- **Validation rules:** require_mitigation
- **Required:** 2 conditions
- **Invalid when:** 1 conditions
- **Feature types:** mitigation
- **Confidence:** min detect 50.0%, high 80.0%

## Relationships

- **bos** → **trend** (strengthens): BOS may strengthen trend continuation when aligned with HTF bias.

- **choch** → **trend** (may_reverse): CHOCH may indicate a potential reversal — not a standalone entry.

- **liquidity_sweep** → **bullish_order_block** (may_strengthen): Liquidity sweep may strengthen a subsequent Order Block reaction.

- **liquidity_sweep** → **bearish_order_block** (may_strengthen): Liquidity sweep may strengthen a subsequent Order Block reaction.

- **bullish_order_block** → **bullish_fvg** (may_reinforce): Order Blocks and FVGs may reinforce each other when overlapping in direction.

- **bearish_order_block** → **bearish_fvg** (may_reinforce): Order Blocks and FVGs may reinforce each other when overlapping in direction.

- **demand_zone** → **discount** (aligned_with): Demand in discount is stronger confluence than demand in premium.

- **supply_zone** → **premium** (aligned_with): Supply in premium is stronger confluence than supply in discount.

- **impulse_move** → **retracement** (followed_by): Impulse moves are often followed by retracements; retracement alone is not entry.

- **higher_high** → **bullish_trend** (defines): Series of HH/HL defines a bullish trend structure.

- **lower_low** → **bearish_trend** (defines): Series of LL/LH defines a bearish trend structure.

- **mitigation** → **bullish_order_block** (consumes): Mitigation may reduce remaining Order Block validity.
