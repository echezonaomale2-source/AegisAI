"""Memory statistics for the AI Memory page."""

from __future__ import annotations

from collections import Counter

from memory.database import connect
from memory.feature_fingerprint import FEATURE_KEYS, bits_to_features
from memory.learning_engine import LearningEngine
from memory.memory_repository import MemoryRepository
from memory.pattern_engine import PatternEngine


class MemoryStatsService:
    def __init__(self) -> None:
        self.repo = MemoryRepository()
        self.learning = LearningEngine()
        self.patterns = PatternEngine()

    def build(self) -> dict:
        base = self.repo.closed_stats()
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT fingerprint_bits, outcome, direction, pair, grade
                FROM memories
                WHERE outcome IN ('TAKE_PROFIT', 'STOP_LOSS')
                """
            ).fetchall()

        win_combos: Counter[str] = Counter()
        loss_combos: Counter[str] = Counter()
        alignment_wins: Counter[str] = Counter()
        grades: Counter[str] = Counter()

        for row in rows:
            features = bits_to_features(row["fingerprint_bits"] or "")
            active = [k for k in FEATURE_KEYS if features.get(k)]
            core = [
                k
                for k in active
                if k
                in {
                    "trend_alignment",
                    "bos",
                    "choch",
                    "liquidity_sweep",
                    "bullish_order_block",
                    "bearish_order_block",
                    "bullish_fvg",
                    "bearish_fvg",
                    "demand_zone",
                    "supply_zone",
                    "direction_buy",
                    "direction_sell",
                }
            ]
            label = " + ".join(core[:5]) if core else "unspecified"
            if row["grade"]:
                grades[row["grade"]] += 1
            if row["outcome"] == "TAKE_PROFIT":
                win_combos[label] += 1
                alignment = "BUY aligned" if features.get("direction_buy") else "SELL aligned"
                if features.get("trend_alignment"):
                    alignment_wins[alignment] += 1
            else:
                loss_combos[label] += 1

        most_successful_combo = win_combos.most_common(1)[0] if win_combos else None
        most_common_loss = loss_combos.most_common(1)[0] if loss_combos else None
        most_alignment = alignment_wins.most_common(1)[0] if alignment_wins else None
        top_patterns = self.patterns.top_patterns(5)
        worst_patterns = self.patterns.worst_patterns(3)

        # Prefer pattern DB for "most successful feature combination" when available.
        if top_patterns:
            best = top_patterns[0]
            combo = {"pattern": best["pattern"], "wins": best["wins"], "trades": best["trades"]}
        elif most_successful_combo:
            combo = {"pattern": most_successful_combo[0], "wins": most_successful_combo[1]}
        else:
            combo = None

        if worst_patterns:
            worst = worst_patterns[0]
            losing = {"pattern": worst["pattern"], "losses": worst["losses"], "trades": worst["trades"]}
        elif most_common_loss:
            losing = {"pattern": most_common_loss[0], "losses": most_common_loss[1]}
        else:
            losing = None

        return {
            **base,
            "most_successful_timeframe_alignment": most_alignment[0] if most_alignment else None,
            "most_successful_feature_combination": combo,
            "most_common_losing_pattern": losing,
            "top_patterns": top_patterns,
            "grade_distribution": dict(grades),
            "adaptive_weights": self.learning.get_adaptive_weights(),
            "feature_performance": self.learning.feature_performance()[:12],
        }
