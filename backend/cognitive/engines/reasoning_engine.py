"""
Engine 5 — Reasoning Engine.

Holistic evaluation of supporting / conflicting / missing evidence.
Not a naive if/else trade rule — scores evidence, detects conflicts,
accounts for image uncertainty and historical bias, then concludes.
Insufficient evidence always yields NO TRADE.
"""

from __future__ import annotations

from cognitive.events import EVT_REASONING_DONE, EventBus
from cognitive.models.evidence import Evidence, EvidenceItem
from cognitive.models.reasoning import ReasoningReport
from cognitive.weights import MIN_CONFIDENCE, MIN_EVIDENCE_SCORE, MIN_MARGIN, TF_MULTIPLIERS
from core.logging_setup import get_logger

log = get_logger("cognitive.reasoning")


class ReasoningEngine:
    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus

    def reason(
        self,
        evidence_by_tf: dict[str, Evidence],
        *,
        historical_bias: float = 0.0,
        pair: str = "Unknown",
    ) -> ReasoningReport:
        aggregated_buy = 0.0
        aggregated_sell = 0.0
        aggregated_neutral = 0.0
        all_items: list[EvidenceItem] = []
        missing: list[str] = []
        supporting_structures: list[str] = []
        conflicting_structures: list[str] = []
        max_uncertainty = 0.0
        empty_tfs: list[str] = []

        for tf, evidence in evidence_by_tf.items():
            mult = TF_MULTIPLIERS.get(tf.upper(), TF_MULTIPLIERS.get(tf, 1.0))
            aggregated_buy += evidence.buy_weight * mult
            aggregated_sell += evidence.sell_weight * mult
            aggregated_neutral += evidence.neutral_weight * mult
            all_items.extend(evidence.items)
            missing.extend([f"{tf}:{m}" for m in evidence.missing_evidence])
            for s in evidence.supporting_structures:
                supporting_structures.append(f"{tf}:{s}")
            for s in evidence.conflicting_structures:
                conflicting_structures.append(f"{tf}:{s}")
            max_uncertainty = max(max_uncertainty, evidence.image_uncertainty)
            if not evidence.items and not evidence.buy_weight and not evidence.sell_weight:
                empty_tfs.append(tf)
                missing.append(f"{tf}:no_items")

        total = aggregated_buy + aggregated_sell + aggregated_neutral
        if total <= 0:
            return self._no_trade(
                pair=pair,
                missing=missing or ["no_evidence"],
                uncertainty=max_uncertainty,
                narrative=["No usable evidence extracted from charts."],
                historical_bias=historical_bias,
                gates_failed=["no_usable_evidence"],
                supporting_structures=supporting_structures,
                conflicting_structures=conflicting_structures,
            )

        # Normalize to 0–100 evidence scores.
        buy_score = 100.0 * aggregated_buy / total
        sell_score = 100.0 * aggregated_sell / total
        neutral_score = 100.0 * aggregated_neutral / total

        # Determine provisional side by evidence mass (not hard-coded feature checks).
        if buy_score >= sell_score and buy_score >= neutral_score:
            provisional = "BUY"
            primary_score = buy_score
            opposing_score = sell_score
        elif sell_score > buy_score and sell_score >= neutral_score:
            provisional = "SELL"
            primary_score = sell_score
            opposing_score = buy_score
        else:
            provisional = "NO TRADE"
            primary_score = max(buy_score, sell_score)
            opposing_score = min(buy_score, sell_score)

        supporting = [i for i in all_items if i.direction == provisional]
        conflicting = [
            i
            for i in all_items
            if i.direction in {"BUY", "SELL"} and i.direction != provisional
        ]
        conflicts_summary = self._conflict_summaries(
            conflicting, missing, evidence_by_tf, conflicting_structures
        )

        # Confidence from evidence margin, strength, uncertainty, history.
        margin = primary_score - opposing_score
        uncertainty_penalty = max_uncertainty * 0.35
        conflict_penalty = min(25.0, len(conflicting) * 2.5 + len(conflicting_structures) * 1.5)
        missing_penalty = min(20.0, len(missing) * 2.0)
        hist = max(-20.0, min(20.0, historical_bias))

        confidence = (
            0.55 * primary_score
            + 0.25 * min(100.0, margin * 2.0)
            + 0.10 * (100.0 - neutral_score)
            + hist
            - uncertainty_penalty
            - conflict_penalty
            - missing_penalty
        )
        confidence = max(0.0, min(100.0, confidence))

        # Gate: insufficient evidence → NO TRADE (never guess).
        conclusion: str = provisional
        narrative: list[str] = []
        gates_failed: list[str] = []

        if max_uncertainty >= 55:
            conclusion = "NO TRADE"
            gates_failed.append("image_uncertainty")
            narrative.append(
                f"Image uncertainty too high ({max_uncertainty:.0f}%) — refusing to trade."
            )
        elif provisional == "NO TRADE":
            conclusion = "NO TRADE"
            gates_failed.append("inconclusive_mass")
            narrative.append("Evidence mass is neutral / inconclusive.")
        elif primary_score < MIN_EVIDENCE_SCORE:
            conclusion = "NO TRADE"
            gates_failed.append("min_evidence_score")
            narrative.append(
                f"{provisional} evidence score {primary_score:.0f} below minimum {MIN_EVIDENCE_SCORE:.0f}."
            )
        elif margin < MIN_MARGIN:
            conclusion = "NO TRADE"
            gates_failed.append("min_margin")
            narrative.append(
                f"Evidence margin {margin:.0f} too thin (need ≥ {MIN_MARGIN:.0f}) — conflict dominates."
            )
        elif confidence < MIN_CONFIDENCE:
            conclusion = "NO TRADE"
            gates_failed.append("min_confidence")
            narrative.append(
                f"Traceable confidence {confidence:.0f}% below {MIN_CONFIDENCE:.0f}% threshold."
            )
        elif self._htf_conflict(evidence_by_tf, provisional):
            conclusion = "NO TRADE"
            gates_failed.append("htf_conflict")
            narrative.append("Higher-timeframe evidence conflicts with provisional side.")
        elif self._structure_stalemate(evidence_by_tf):
            conclusion = "NO TRADE"
            gates_failed.append("structure_stalemate")
            narrative.append(
                "Supporting and conflicting structures are too evenly matched — prefer NO TRADE."
            )
        elif empty_tfs and len(empty_tfs) >= 2:
            conclusion = "NO TRADE"
            gates_failed.append("missing_timeframes")
            narrative.append(
                f"Insufficient timeframe coverage ({', '.join(empty_tfs)}) — prefer NO TRADE."
            )
        else:
            narrative.append(
                f"Evidence supports {provisional}: score {primary_score:.0f} vs opposing {opposing_score:.0f}."
            )

        if conflicts_summary:
            narrative.append("Conflicts: " + "; ".join(conflicts_summary[:4]))
        if missing:
            narrative.append("Missing (not invented): " + ", ".join(missing[:6]))
        if supporting_structures and conclusion in {"BUY", "SELL"}:
            narrative.append(
                "Supporting structures: " + ", ".join(supporting_structures[:6])
            )

        # Recompute supporting if conclusion flipped to NO TRADE
        if conclusion == "NO TRADE":
            supporting = sorted(all_items, key=lambda i: i.weight, reverse=True)[:8]
            conflicting = [i for i in all_items if i.direction in {"BUY", "SELL"}]

        explanation = " ".join(narrative)

        report = ReasoningReport(
            pair=pair,
            buy_evidence_score=round(buy_score, 1),
            sell_evidence_score=round(sell_score, 1),
            neutral_score=round(neutral_score, 1),
            supporting=supporting[:12],
            conflicting=conflicting[:12],
            missing=missing,
            supporting_structures=supporting_structures[:24],
            conflicting_structures=conflicting_structures[:24],
            image_uncertainty=max_uncertainty,
            historical_bias=hist,
            conclusion=conclusion,  # type: ignore[arg-type]
            confidence=round(confidence, 1),
            conflicts_summary=conflicts_summary,
            narrative=narrative,
            explanation=explanation,
            gates_failed=gates_failed,
            evidence_snapshot=self._merge_evidence(evidence_by_tf),
            trace={
                "buy_score": round(buy_score, 2),
                "sell_score": round(sell_score, 2),
                "neutral_score": round(neutral_score, 2),
                "margin": round(margin, 2),
                "uncertainty_penalty": round(uncertainty_penalty, 2),
                "conflict_penalty": round(conflict_penalty, 2),
                "missing_penalty": round(missing_penalty, 2),
                "historical_bias": round(hist, 2),
                "confidence": round(confidence, 2),
                "gates_failed_count": float(len(gates_failed)),
            },
        )
        log.info(
            "reasoning pair=%s conclusion=%s conf=%.1f buy=%.1f sell=%.1f gates=%s",
            pair,
            conclusion,
            confidence,
            buy_score,
            sell_score,
            gates_failed or ["none"],
        )
        if self._bus:
            self._bus.publish(
                EVT_REASONING_DONE,
                {"conclusion": conclusion, "confidence": confidence, "pair": pair},
            )
        return report

    def _no_trade(
        self,
        *,
        pair: str,
        missing: list[str],
        uncertainty: float,
        narrative: list[str],
        historical_bias: float,
        gates_failed: list[str] | None = None,
        supporting_structures: list[str] | None = None,
        conflicting_structures: list[str] | None = None,
    ) -> ReasoningReport:
        gates = gates_failed or ["no_usable_evidence"]
        return ReasoningReport(
            pair=pair,
            conclusion="NO TRADE",
            confidence=0.0,
            missing=missing,
            supporting_structures=supporting_structures or [],
            conflicting_structures=conflicting_structures or [],
            image_uncertainty=uncertainty,
            historical_bias=historical_bias,
            narrative=narrative,
            explanation=" ".join(narrative),
            gates_failed=gates,
            trace={"confidence": 0.0, "reason": 0.0, "gates_failed_count": float(len(gates))},
        )

    def _conflict_summaries(
        self,
        conflicting: list[EvidenceItem],
        missing: list[str],
        evidence_by_tf: dict[str, Evidence],
        conflicting_structures: list[str],
    ) -> list[str]:
        summaries: list[str] = []
        for item in sorted(conflicting, key=lambda i: i.weight, reverse=True)[:5]:
            summaries.append(f"{item.timeframe} {item.name} ({item.direction})")
        for label in conflicting_structures[:5]:
            summaries.append(f"Structure conflict: {label}")
        for tf, ev in evidence_by_tf.items():
            for item in ev.items:
                if item.feature_type == "supply_zone" and item.direction == "SELL":
                    summaries.append(f"Nearby resistance / supply on {tf}")
                if item.feature_type == "bos" and item.strength in {"Weak", "Very Weak"}:
                    summaries.append(f"Weak BOS on {tf}")
        seen: set[str] = set()
        out: list[str] = []
        for s in summaries:
            if s not in seen:
                seen.add(s)
                out.append(s)
        return out

    def _htf_conflict(self, evidence_by_tf: dict[str, Evidence], side: str) -> bool:
        """If 4H strongly opposes the provisional side, block the trade."""
        h4 = evidence_by_tf.get("4H")
        if h4 is None:
            return False
        if side == "BUY" and h4.sell_weight > h4.buy_weight * 1.35 and h4.sell_weight > 8:
            return True
        if side == "SELL" and h4.buy_weight > h4.sell_weight * 1.35 and h4.buy_weight > 8:
            return True
        # Prefer Evidence.dominant_direction when present
        if h4.dominant_direction in {"BUY", "SELL"} and h4.dominant_direction != side:
            if max(h4.buy_weight, h4.sell_weight) > 8:
                return True
        return False

    def _structure_stalemate(self, evidence_by_tf: dict[str, Evidence]) -> bool:
        """Even support/conflict across timeframes → prefer NO TRADE."""
        support_n = conflict_n = 0
        for ev in evidence_by_tf.values():
            support_n += len(ev.supporting_structures)
            conflict_n += len(ev.conflicting_structures)
            if abs(ev.buy_weight - ev.sell_weight) < 3.0 and min(ev.buy_weight, ev.sell_weight) > 5:
                return True
        if support_n == 0 and conflict_n == 0:
            return False
        if conflict_n >= support_n and conflict_n >= 2:
            return True
        return False

    def _merge_evidence(self, evidence_by_tf: dict[str, Evidence]) -> Evidence:
        items: list[EvidenceItem] = []
        buy = sell = neu = 0.0
        missing: list[str] = []
        supporting: list[str] = []
        conflicting: list[str] = []
        unc = 0.0
        for ev in evidence_by_tf.values():
            items.extend(ev.items)
            buy += ev.buy_weight
            sell += ev.sell_weight
            neu += ev.neutral_weight
            missing.extend(ev.missing_evidence)
            supporting.extend(ev.supporting_structures)
            conflicting.extend(ev.conflicting_structures)
            unc = max(unc, ev.image_uncertainty)
        if buy > sell and buy > 0:
            dominant = "BUY"
        elif sell > buy and sell > 0:
            dominant = "SELL"
        else:
            dominant = "NEUTRAL"
        return Evidence(
            items=items,
            buy_weight=buy,
            sell_weight=sell,
            neutral_weight=neu,
            dominant_direction=dominant,  # type: ignore[arg-type]
            image_uncertainty=unc,
            supporting_structures=supporting,
            conflicting_structures=conflicting,
            missing_evidence=missing,
        )
