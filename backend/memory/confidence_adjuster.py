"""Multi-factor confidence adjustment (history + quality + alignment + similarity)."""

from __future__ import annotations

from dataclasses import dataclass

from memory.pattern_engine import PatternEngine
from memory.similarity_engine import SimilarityReport
from models.decision_schemas import TradeDecision

MIN_SIMILAR_FOR_ADJUSTMENT = 15
MIN_PATTERN_TRADES = 20
MAX_CONFIDENCE_BOOST = 14.0
MAX_CONFIDENCE_PENALTY = 16.0


@dataclass
class ConfidenceAdjustment:
    base_confidence: float
    adjusted_confidence: float
    delta: float
    similar_count: int
    tp_count: int
    sl_count: int
    historical_win_rate: float | None
    applied: bool
    reason: str
    factors: dict[str, float]


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


class ConfidenceAdjuster:
    def __init__(self) -> None:
        self.patterns = PatternEngine()

    def adjust(
        self,
        base_confidence: float,
        report: SimilarityReport,
        decision: TradeDecision | None = None,
        fingerprint_bits: str | None = None,
    ) -> ConfidenceAdjustment:
        factors = {
            "historical_pattern_success": 50.0,
            "image_quality": 70.0,
            "market_structure_quality": 60.0,
            "liquidity_quality": 55.0,
            "order_block_strength": 55.0,
            "timeframe_alignment": 55.0,
            "pattern_similarity": 50.0,
        }

        closed = report.tp_count + report.sl_count
        if report.win_rate is not None and closed >= MIN_SIMILAR_FOR_ADJUSTMENT:
            factors["historical_pattern_success"] = report.win_rate
            factors["pattern_similarity"] = min(100.0, 50.0 + (report.win_rate - 50.0) * 0.8)

        if decision is not None:
            charts = (decision.analysis_4h, decision.analysis_1h, decision.analysis_15m)
            ok = sum(1 for c in charts if c.status == "ok")
            factors["image_quality"] = (ok / 3.0) * 100.0
            aligned = (
                decision.analysis_4h.trend == decision.analysis_1h.trend
                and decision.analysis_4h.trend in {"Bullish", "Bearish"}
            )
            factors["timeframe_alignment"] = 90.0 if aligned else 35.0
            structure_hits = sum(
                1
                for c in charts
                if c.market_structure not in {"Unknown", ""} and (c.bos or c.choch or c.swing_high_count >= 2)
            )
            factors["market_structure_quality"] = min(100.0, 40.0 + structure_hits * 20.0)
            liq_hits = sum(1 for c in charts if c.liquidity_sweep or c.equal_highs or c.equal_lows)
            factors["liquidity_quality"] = min(100.0, 35.0 + liq_hits * 22.0)
            if decision.overall_bias == "BUY":
                ob = any(c.bullish_order_block for c in charts)
            elif decision.overall_bias == "SELL":
                ob = any(c.bearish_order_block for c in charts)
            else:
                ob = False
            factors["order_block_strength"] = 85.0 if ob else 45.0

        pattern_bonus = 0.0
        pattern_note = ""
        if fingerprint_bits:
            pattern = self.patterns.get(fingerprint_bits)
            if pattern and (pattern["trades"] or 0) >= MIN_PATTERN_TRADES and pattern["win_rate"] is not None:
                factors["historical_pattern_success"] = (
                    factors["historical_pattern_success"] * 0.4 + pattern["win_rate"] * 0.6
                )
                edge = (pattern["win_rate"] - 50.0) / 50.0
                strength = min(1.0, pattern["trades"] / 100.0)
                pattern_bonus = edge * 8.0 * strength
                pattern_note = (
                    f" Pattern DB: {pattern['trades']} trades, "
                    f"win rate {pattern['win_rate']:.1f}%."
                )

        # Weighted blend of factors → target confidence prior
        weights = {
            "historical_pattern_success": 0.28,
            "image_quality": 0.10,
            "market_structure_quality": 0.15,
            "liquidity_quality": 0.12,
            "order_block_strength": 0.10,
            "timeframe_alignment": 0.15,
            "pattern_similarity": 0.10,
        }
        factor_score = sum(factors[k] * weights[k] for k in weights)

        if closed < MIN_SIMILAR_FOR_ADJUSTMENT and not pattern_note:
            blended = base_confidence * 0.75 + factor_score * 0.25
            adjusted = _clamp(blended)
            return ConfidenceAdjustment(
                base_confidence=base_confidence,
                adjusted_confidence=round(adjusted, 1),
                delta=round(adjusted - base_confidence, 2),
                similar_count=closed,
                tp_count=report.tp_count,
                sl_count=report.sl_count,
                historical_win_rate=report.win_rate,
                applied=True,
                reason=(
                    f"Multi-factor confidence blend applied "
                    f"(similar closed trades {closed}/{MIN_SIMILAR_FOR_ADJUSTMENT} — "
                    f"historical influence limited).{pattern_note}"
                ),
                factors={k: round(v, 1) for k, v in factors.items()},
            )

        # Full historical influence
        strength = min(1.0, max(closed, 1) / 100.0)
        edge = ((report.win_rate or 50.0) - 50.0) / 50.0
        hist_delta = edge * (MAX_CONFIDENCE_BOOST if edge >= 0 else MAX_CONFIDENCE_PENALTY) * strength
        quality_delta = (factor_score - base_confidence) * 0.25
        delta = hist_delta + quality_delta + pattern_bonus
        delta = max(-MAX_CONFIDENCE_PENALTY, min(MAX_CONFIDENCE_BOOST, delta))
        adjusted = _clamp(base_confidence + delta)

        return ConfidenceAdjustment(
            base_confidence=base_confidence,
            adjusted_confidence=round(adjusted, 1),
            delta=round(delta, 2),
            similar_count=closed,
            tp_count=report.tp_count,
            sl_count=report.sl_count,
            historical_win_rate=report.win_rate,
            applied=True,
            reason=(
                f"Found {closed} similar historical trades "
                f"(TP {report.tp_count} / SL {report.sl_count}"
                + (
                    f", win rate {report.win_rate:.1f}%"
                    if report.win_rate is not None
                    else ""
                )
                + f"). Confidence adjusted by {delta:+.1f}.{pattern_note}"
            ),
            factors={k: round(v, 1) for k, v in factors.items()},
        )
