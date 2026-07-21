"""Engine 4 — Evidence Engine: FeatureCollection → Evidence."""

from __future__ import annotations

import hashlib

from cognitive.events import EVT_EVIDENCE_BUILT, EventBus
from cognitive.models.evidence import (
    Evidence,
    EvidenceItem,
    EvidenceReport,
    EvidenceStrength,
)
from cognitive.models.features import CognitiveFeature, FeatureCollection
from cognitive.weights import DEFAULT_FEATURE_WEIGHTS
from core.logging_setup import get_logger

log = get_logger("cognitive.evidence")


def strength_from_confidence(confidence: float) -> EvidenceStrength:
    if confidence >= 90:
        return "Very Strong"
    if confidence >= 75:
        return "Strong"
    if confidence >= 55:
        return "Medium"
    if confidence >= 35:
        return "Weak"
    return "Very Weak"


class EvidenceEngine:
    """
    Evaluate every validated feature into directional evidence with strength
    and weight. Records supporting vs conflicting structures. Never invents
    features — only evaluates what Knowledge-gated FeatureExtraction produced.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    def evaluate(
        self,
        features: FeatureCollection,
        *,
        image_quality: float = 100.0,
        feature_weights: dict[str, float] | None = None,
    ) -> Evidence:
        weights = {**DEFAULT_FEATURE_WEIGHTS, **(feature_weights or {})}
        items: list[EvidenceItem] = []
        buy_w = sell_w = neu_w = 0.0
        skipped: list[str] = []

        quality_factor = max(0.2, min(1.0, image_quality / 100.0))

        for feat in features.features:
            if feat.feature_type == "unknown" or feat.confidence <= 0:
                skipped.append(feat.name or feat.feature_type or "unknown")
                continue
            direction = self._resolve_direction(feat)
            base = weights.get(feat.feature_type, 5.0)
            # Weight scaled by confidence and image quality.
            weight = base * (feat.confidence / 100.0) * quality_factor
            strength = strength_from_confidence(feat.confidence)
            trace = hashlib.sha1(
                f"{features.timeframe}:{feat.feature_type}:{feat.name}:{feat.confidence}".encode()
            ).hexdigest()[:12]
            structures = self._item_structures(feat)

            item = EvidenceItem(
                id=f"{features.timeframe}:{feat.feature_type}:{len(items)}",
                name=feat.name,
                feature_type=feat.feature_type,
                direction=direction,  # type: ignore[arg-type]
                strength=strength,
                weight=round(weight, 3),
                confidence=feat.confidence,
                timeframe=features.timeframe,
                supporting_candles=list(feat.supporting_candles),
                supporting_structures=structures,
                source_feature=feat,
                rationale=(
                    f"{feat.name} on {features.timeframe} → {direction} "
                    f"({strength}, w={weight:.1f}, conf={feat.confidence:.0f}%)"
                ),
                trace_id=trace,
            )
            items.append(item)
            if direction == "BUY":
                buy_w += weight
            elif direction == "SELL":
                sell_w += weight
            else:
                neu_w += weight

        dominant = self._dominant_direction(buy_w, sell_w, neu_w)
        supporting, conflicting = self._partition_structures(items, dominant)

        uncertainty = max(0.0, min(100.0, 100.0 - image_quality))
        notes = list(features.notes)
        if skipped:
            notes.append(f"Skipped non-evidence features: {', '.join(skipped[:8])}")
        if conflicting:
            notes.append(
                f"Conflicting structures vs {dominant}: {', '.join(conflicting[:6])}"
            )

        evidence = Evidence(
            items=items,
            buy_weight=round(buy_w, 3),
            sell_weight=round(sell_w, 3),
            neutral_weight=round(neu_w, 3),
            dominant_direction=dominant,  # type: ignore[arg-type]
            image_uncertainty=uncertainty,
            supporting_structures=supporting,
            conflicting_structures=conflicting,
            missing_evidence=list(features.missing),
            notes=notes,
        )
        log.info(
            "evidence tf=%s buy=%.1f sell=%.1f neutral=%.1f items=%d dominant=%s",
            features.timeframe,
            buy_w,
            sell_w,
            neu_w,
            len(items),
            dominant,
        )
        if self._bus:
            self._bus.publish(
                EVT_EVIDENCE_BUILT,
                {
                    "timeframe": features.timeframe,
                    "buy": buy_w,
                    "sell": sell_w,
                    "items": len(items),
                    "dominant": dominant,
                },
            )
        return evidence

    def report(self, evidence: Evidence, *, timeframe: str = "Unknown", pair: str = "Unknown") -> EvidenceReport:
        """Generate an explainable evidence report from evaluated Evidence."""
        summary = (
            f"{timeframe} {pair}: dominant={evidence.dominant_direction} "
            f"BUY={evidence.buy_weight:.1f} SELL={evidence.sell_weight:.1f} "
            f"NEUTRAL={evidence.neutral_weight:.1f}; "
            f"support={len(evidence.supporting_structures)} "
            f"conflict={len(evidence.conflicting_structures)} "
            f"missing={len(evidence.missing_evidence)}"
        )
        return EvidenceReport(
            timeframe=timeframe,
            pair=pair,
            buy_weight=evidence.buy_weight,
            sell_weight=evidence.sell_weight,
            neutral_weight=evidence.neutral_weight,
            dominant_direction=evidence.dominant_direction,
            item_count=len(evidence.items),
            items=list(evidence.items),
            supporting_structures=list(evidence.supporting_structures),
            conflicting_structures=list(evidence.conflicting_structures),
            missing_evidence=list(evidence.missing_evidence),
            image_uncertainty=evidence.image_uncertainty,
            notes=list(evidence.notes),
            summary=summary,
        )

    def report_multi(
        self,
        evidence_by_tf: dict[str, Evidence],
        *,
        pair: str = "Unknown",
    ) -> dict[str, EvidenceReport]:
        return {
            tf: self.report(ev, timeframe=tf, pair=pair)
            for tf, ev in evidence_by_tf.items()
        }

    def _resolve_direction(self, feat: CognitiveFeature) -> str:
        if feat.direction_hint in {"BUY", "SELL", "NEUTRAL"}:
            return feat.direction_hint
        # Conservative: unknown hint → NEUTRAL (never guess BUY/SELL).
        return "NEUTRAL"

    def _item_structures(self, feat: CognitiveFeature) -> list[str]:
        labels = [feat.feature_type]
        if feat.name and feat.name.lower() != feat.feature_type.lower():
            labels.append(feat.name)
        loc = feat.location or {}
        kind = loc.get("kind")
        if kind:
            labels.append(str(kind))
        return labels

    @staticmethod
    def _dominant_direction(buy_w: float, sell_w: float, neu_w: float) -> str:
        if buy_w <= 0 and sell_w <= 0:
            return "NEUTRAL"
        if buy_w > sell_w and buy_w >= neu_w * 0.5:
            return "BUY"
        if sell_w > buy_w and sell_w >= neu_w * 0.5:
            return "SELL"
        if abs(buy_w - sell_w) < 1e-9:
            return "NEUTRAL"
        return "BUY" if buy_w > sell_w else "SELL"

    @staticmethod
    def _partition_structures(
        items: list[EvidenceItem],
        dominant: str,
    ) -> tuple[list[str], list[str]]:
        supporting: list[str] = []
        conflicting: list[str] = []
        seen_s: set[str] = set()
        seen_c: set[str] = set()

        for item in items:
            label = f"{item.feature_type}:{item.name}"
            if dominant == "NEUTRAL":
                if item.direction == "NEUTRAL":
                    if label not in seen_s:
                        supporting.append(label)
                        seen_s.add(label)
                continue
            if item.direction == dominant:
                if label not in seen_s:
                    supporting.append(label)
                    seen_s.add(label)
            elif item.direction in {"BUY", "SELL"} and item.direction != dominant:
                if label not in seen_c:
                    conflicting.append(label)
                    seen_c.add(label)
        return supporting, conflicting
