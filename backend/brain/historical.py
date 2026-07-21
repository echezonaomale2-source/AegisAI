"""
Historical support from memory — influences confidence, never overrides chart analysis.
"""

from __future__ import annotations

from brain.models import HistoricalSupport
from memory.feature_fingerprint import build_fingerprint
from memory.memory_service import MemoryService
from models.decision_schemas import TradeDecision


class HistoricalReasoner:
    """
    Search similar memories / patterns.

    Historical evidence adjusts confidence modestly.
    It must NEVER flip the chart-derived directional bias by itself.
    """

    MAX_INFLUENCE = 8.0
    MIN_SIMILAR = 10

    def __init__(self, memory: MemoryService | None = None) -> None:
        self.memory = memory or MemoryService()

    def evaluate(self, decision: TradeDecision) -> HistoricalSupport:
        if decision.overall_bias == "NO TRADE":
            return HistoricalSupport(
                historical_support="None",
                notes=["NO TRADE — historical pattern search skipped for directional support."],
            )

        fingerprint = build_fingerprint(decision)
        bits = fingerprint["bits"]
        if isinstance(bits, list):
            bits = "".join(str(b) for b in bits)

        report = self.memory.similarity.find_similar(
            bits,
            direction=decision.overall_bias,
            pair=decision.pair,
        )

        similar_count = len(report.similar)
        tp = report.tp_count
        sl = report.sl_count
        closed = tp + sl
        win_rate = report.win_rate
        if win_rate is not None and win_rate <= 1.0:
            win_rate = win_rate * 100.0

        similarity = None
        if report.similar:
            similarity = max(s.similarity for s in report.similar) * 100.0

        strength = "Unknown"
        influence = 0.0
        notes: list[str] = []

        if similar_count < self.MIN_SIMILAR or closed < 5:
            strength = "Weak"
            influence = -3.0
            notes.append(
                f"Weak historical sample (similar={similar_count}, closed={closed}) — reducing confidence."
            )
        elif win_rate is not None:
            if win_rate >= 70 and similar_count >= 20:
                strength = "Strong"
                influence = min(self.MAX_INFLUENCE, (win_rate - 55) * 0.25)
                notes.append(
                    f"Strong historical support: {tp}W/{sl}L ({win_rate:.0f}% WR) over {similar_count} similar."
                )
            elif win_rate >= 55:
                strength = "Moderate"
                influence = min(self.MAX_INFLUENCE * 0.6, (win_rate - 50) * 0.2)
                notes.append(f"Moderate historical support ({win_rate:.0f}% WR).")
            else:
                strength = "Weak"
                influence = -min(self.MAX_INFLUENCE, (55 - win_rate) * 0.3)
                notes.append(
                    f"Weak historical outcomes ({win_rate:.0f}% WR) — reducing confidence."
                )

        influence = max(-self.MAX_INFLUENCE, min(self.MAX_INFLUENCE, influence))
        notes.append("Historical evidence influences confidence but does not override chart analysis.")

        return HistoricalSupport(
            pattern_similarity=round(float(similarity), 1) if similarity is not None else None,
            previous_similar_analyses=int(similar_count),
            wins=int(tp),
            losses=int(sl),
            historical_support=strength,  # type: ignore[arg-type]
            influence_on_confidence=round(influence, 2),
            notes=notes,
        )
