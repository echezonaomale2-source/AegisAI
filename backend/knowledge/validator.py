"""
Validate detected features against Knowledge Engine rules.

Never marks a concept valid unless required conditions pass and no invalid
conditions trigger. Incomplete → Unknown (never guess).
"""

from __future__ import annotations

from typing import Any

from cognitive.models.features import CognitiveFeature, FeatureCollection
from cognitive.models.market import MarketModel
from knowledge.conditions import describe_failure, evaluate_condition, evaluate_named_rule
from knowledge.models import ConceptDefinition, ValidationResult
from knowledge.registry import KnowledgeRegistry, get_registry
from knowledge.versioning import CURRENT_VERSION


def build_context(
    market: MarketModel | None = None,
    *,
    feature: CognitiveFeature | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a flat/nested validation context from MarketModel + feature."""
    ctx: dict[str, Any] = {
        "market_usable": False,
        "candle_count": 0,
        "bos": False,
        "choch": False,
        "trend": {"direction": "Unknown", "confidence": 0.0},
        "premium": "Unknown",
        "discount": "Unknown",
        "has_higher_high": False,
        "has_higher_low": False,
        "has_lower_high": False,
        "has_lower_low": False,
        "has_bullish_ob": False,
        "has_bearish_ob": False,
        "has_bullish_fvg": False,
        "has_bearish_fvg": False,
        "has_liquidity": False,
        "has_internal_liquidity": False,
        "has_external_liquidity": False,
        "has_liquidity_sweep": False,
        "has_supply": False,
        "has_demand": False,
        "has_impulse": False,
        "has_retracement": False,
        "has_mitigation": False,
        "feature_confidence": 0.0,
        "feature_type": None,
    }

    if market is not None:
        ctx["market_usable"] = market.is_usable
        ctx["candle_count"] = len(market.candles)
        ctx["bos"] = market.bos
        ctx["choch"] = market.choch
        ctx["trend"] = {
            "direction": market.trend.direction,
            "confidence": market.trend.confidence,
        }
        ctx["premium"] = market.premium
        ctx["discount"] = market.discount
        ctx["has_higher_high"] = any(s.structure_label == "HH" for s in market.swing_points)
        ctx["has_higher_low"] = any(s.structure_label == "HL" for s in market.swing_points)
        ctx["has_lower_high"] = any(s.structure_label == "LH" for s in market.swing_points)
        ctx["has_lower_low"] = any(s.structure_label == "LL" for s in market.swing_points)
        # Also infer from structure label text
        label = (market.structure_label or "").lower()
        if "higher high" in label:
            ctx["has_higher_high"] = True
        if "higher low" in label:
            ctx["has_higher_low"] = True
        if "lower high" in label:
            ctx["has_lower_high"] = True
        if "lower low" in label:
            ctx["has_lower_low"] = True

        ctx["has_bullish_ob"] = any(o.side == "bullish" for o in market.order_blocks)
        ctx["has_bearish_ob"] = any(o.side == "bearish" for o in market.order_blocks)
        ctx["has_bullish_fvg"] = any(g.side == "bullish" for g in market.fair_value_gaps)
        ctx["has_bearish_fvg"] = any(g.side == "bearish" for g in market.fair_value_gaps)
        ctx["has_liquidity"] = bool(market.liquidity)
        ctx["has_liquidity_sweep"] = any(
            z.kind == "sweep" or z.swept for z in market.liquidity
        )
        ctx["has_internal_liquidity"] = any(
            z.kind == "internal" for z in market.liquidity
        ) or (len(market.swing_points) >= 4)
        ctx["has_external_liquidity"] = any(
            z.kind == "external" for z in market.liquidity
        ) or (
            any(s.kind == "high" for s in market.swing_points)
            and any(s.kind == "low" for s in market.swing_points)
        )
        ctx["has_supply"] = bool(market.supply)
        ctx["has_demand"] = bool(market.demand)
        ctx["has_impulse"] = market.trend.impulse_move
        ctx["has_retracement"] = market.trend.pullback
        ctx["has_mitigation"] = any(o.mitigated for o in market.order_blocks)

    if feature is not None:
        ctx["feature_confidence"] = feature.confidence
        ctx["feature_type"] = feature.feature_type
        # Feature presence reinforces boolean flags
        ft = feature.feature_type
        if ft == "bos":
            ctx["bos"] = True
        if ft == "choch":
            ctx["choch"] = True
        if ft == "higher_high":
            ctx["has_higher_high"] = True
        if ft == "higher_low":
            ctx["has_higher_low"] = True
        if ft == "lower_high":
            ctx["has_lower_high"] = True
        if ft == "lower_low":
            ctx["has_lower_low"] = True
        if ft == "bullish_order_block":
            ctx["has_bullish_ob"] = True
        if ft == "bearish_order_block":
            ctx["has_bearish_ob"] = True
        if ft == "bullish_fvg":
            ctx["has_bullish_fvg"] = True
        if ft == "bearish_fvg":
            ctx["has_bearish_fvg"] = True
        if ft in {"liquidity", "equal_highs", "equal_lows"}:
            ctx["has_liquidity"] = True
        if ft == "internal_liquidity" or (
            ft == "liquidity" and (feature.location or {}).get("kind") == "internal"
        ):
            ctx["has_internal_liquidity"] = True
            ctx["has_liquidity"] = True
        if ft == "external_liquidity" or (
            ft == "liquidity" and (feature.location or {}).get("kind") == "external"
        ):
            ctx["has_external_liquidity"] = True
            ctx["has_liquidity"] = True
        if ft == "liquidity_sweep":
            ctx["has_liquidity_sweep"] = True
        if ft == "supply_zone":
            ctx["has_supply"] = True
        if ft == "demand_zone":
            ctx["has_demand"] = True
        if ft == "premium":
            ctx["premium"] = "Yes"
        if ft == "discount":
            ctx["discount"] = "Yes"
        if ft == "impulse":
            ctx["has_impulse"] = True
        if ft == "pullback":
            ctx["has_retracement"] = True
        if ft == "mitigation":
            ctx["has_mitigation"] = True
        if ft == "trend" and feature.direction_hint == "BUY":
            ctx["trend"] = {"direction": "Bullish", "confidence": feature.confidence}
        if ft == "trend" and feature.direction_hint == "SELL":
            ctx["trend"] = {"direction": "Bearish", "confidence": feature.confidence}
        if ft == "range":
            ctx["trend"] = {"direction": "Range", "confidence": feature.confidence}

    if overrides:
        ctx.update(overrides)
    return ctx


class KnowledgeValidator:
    def __init__(self, registry: KnowledgeRegistry | None = None) -> None:
        self.registry = registry or get_registry()

    def validate_concept(
        self,
        concept: ConceptDefinition,
        context: dict[str, Any],
    ) -> ValidationResult:
        failed_required: list[str] = []
        triggered_invalid: list[str] = []

        for cond in concept.required_conditions:
            if not evaluate_condition(cond, context):
                failed_required.append(describe_failure(cond, context))

        for cond in concept.invalid_conditions:
            if evaluate_condition(cond, context):
                triggered_invalid.append(describe_failure(cond, context))

        # Incomplete / unusable market → Unknown (never guess)
        if not context.get("market_usable", False) and concept.id not in {"trend"}:
            return ValidationResult(
                concept_id=concept.id,
                concept_name=concept.name,
                status="unknown",
                confidence=0.0,
                knowledge_version=concept.version,
                failed_required=failed_required or ["market not usable"],
                notes=["Incomplete market context — returning Unknown."],
            )

        if failed_required or triggered_invalid:
            # If required missing → unknown when context incomplete; invalid when explicitly contradicted
            status = "invalid" if triggered_invalid else "unknown"
            return ValidationResult(
                concept_id=concept.id,
                concept_name=concept.name,
                status=status,  # type: ignore[arg-type]
                confidence=0.0,
                knowledge_version=concept.version,
                failed_required=failed_required,
                triggered_invalid=triggered_invalid,
                notes=["Validation rules not satisfied."],
            )

        # Named catalog validation_rules:
        # prefer_* → soft notes; require_* are documented by required_conditions (SSOT).
        rule_notes: list[str] = []
        for rule in concept.validation_rules:
            ok, desc, soft = evaluate_named_rule(rule, context)
            if soft and not ok:
                rule_notes.append(f"Preference not met: {desc}")
            elif (not soft) and (not ok) and (not concept.required_conditions):
                # Only hard-enforce named require_* when concept has no declarative conditions
                return ValidationResult(
                    concept_id=concept.id,
                    concept_name=concept.name,
                    status="unknown",
                    confidence=0.0,
                    knowledge_version=concept.version,
                    failed_required=[desc],
                    notes=["Named validation rule(s) not satisfied."],
                )

        conf = float(
            context.get("feature_confidence")
            or (context.get("trend") or {}).get("confidence")
            or 0
        )
        # Structural contexts (rule tests / API) may omit numeric confidence —
        # use min_detect as baseline rather than inventing a high score.
        if conf <= 0:
            conf = concept.confidence_guidelines.min_detect
        min_detect = concept.confidence_guidelines.min_detect
        if conf < min_detect:
            return ValidationResult(
                concept_id=concept.id,
                concept_name=concept.name,
                status="unknown",
                confidence=conf,
                knowledge_version=concept.version,
                notes=[f"Confidence {conf:.0f}% below min_detect {min_detect:.0f}%."] + rule_notes,
            )

        # Relationship awareness (notes only — never invents a trade)
        for rel in self.registry.relationships_for(concept.id):
            rule_notes.append(
                f"Relationship {rel.source}→{rel.target} ({rel.relation}): {rel.description} "
                f"(does not guarantee a trade)."
            )

        return ValidationResult(
            concept_id=concept.id,
            concept_name=concept.name,
            status="valid",
            confidence=conf,
            knowledge_version=concept.version,
            notes=["All validation rules satisfied."] + rule_notes,
        )

    def validate_feature(
        self,
        feature: CognitiveFeature,
        market: MarketModel | None = None,
    ) -> ValidationResult | None:
        concept = self._resolve_concept_for_feature(feature)
        if concept is None:
            return ValidationResult(
                concept_id="unknown",
                concept_name="Unknown",
                status="unknown",
                confidence=0.0,
                knowledge_version=self.registry.version,
                notes=[f"No knowledge concept mapped for feature_type={feature.feature_type}"],
            )

        ctx = build_context(market, feature=feature)
        return self.validate_concept(concept, ctx)

    def _resolve_concept_for_feature(self, feature: CognitiveFeature) -> ConceptDefinition | None:
        """Pick the best catalog concept for a feature — never invent."""
        ft = feature.feature_type
        kind = (feature.location or {}).get("kind")
        name = (feature.name or "").lower()

        if ft == "trend":
            if feature.direction_hint == "BUY":
                return self.registry.get_concept("bullish_trend")
            if feature.direction_hint == "SELL":
                return self.registry.get_concept("bearish_trend")
        if ft == "range":
            return self.registry.get_concept("range")

        # Disambiguate shared "liquidity" feature type
        if ft == "liquidity" or ft in {"internal_liquidity", "external_liquidity"}:
            if ft == "internal_liquidity" or kind == "internal" or "internal" in name:
                return self.registry.get_concept("internal_liquidity")
            if ft == "external_liquidity" or kind == "external" or "external" in name:
                return self.registry.get_concept("external_liquidity")
            return self.registry.get_concept("liquidity")

        concepts = self.registry.concepts_for_feature(ft)
        if not concepts:
            return None
        # Prefer exact concept id match when feature_type equals concept id
        for c in concepts:
            if c.id == ft:
                return c
        return concepts[0]

    def validate_feature_collection(
        self,
        features: FeatureCollection,
        market: MarketModel | None = None,
    ) -> FeatureCollection:
        """
        Return a FeatureCollection containing only knowledge-validated features.
        Invalid/unknown detections are dropped or marked unknown — never guessed valid.
        """
        kept: list[CognitiveFeature] = []
        missing = list(features.missing)
        notes = list(features.notes)
        notes.append(f"Knowledge validation version {self.registry.version}")

        for feat in features.features:
            result = self.validate_feature(feat, market)
            if result is None:
                continue
            if result.status == "valid":
                kept.append(
                    feat.model_copy(
                        update={
                            "notes": list(feat.notes)
                            + [f"Validated by knowledge {result.knowledge_version}: {result.concept_id}"],
                            "confidence": min(feat.confidence, result.confidence or feat.confidence),
                        }
                    )
                )
            else:
                missing.append(f"{feat.feature_type}:{result.status}")
                notes.append(
                    f"Rejected {feat.feature_type} → {result.status} "
                    f"({', '.join(result.failed_required + result.triggered_invalid + result.notes)[:160]})"
                )

        confidences = [f.confidence for f in kept]
        overall = sum(confidences) / len(confidences) if confidences else 0.0
        return FeatureCollection(
            timeframe=features.timeframe,
            pair=features.pair,
            features=kept,
            overall_confidence=overall,
            missing=missing,
            notes=notes,
        )
