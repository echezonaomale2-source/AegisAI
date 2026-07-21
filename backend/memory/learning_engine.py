"""Learning engine — updates feature stats and adaptive weights without changing SMC rules."""

from __future__ import annotations

from datetime import datetime, timezone

from decision.confidence_engine import WEIGHTS
from memory.database import connect
from memory.feature_fingerprint import bits_to_features
from memory.outcome_utils import is_loss, is_neutral, is_win, normalize_outcome

# Never learn from tiny samples.
MIN_SAMPLES_FOR_WEIGHT_UPDATE = 20
MIN_SAMPLES_FOR_FEATURE_INFLUENCE = 12
MAX_WEIGHT_DELTA = 0.015  # per learning event, small


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class LearningEngine:
    """
    Adjusts confidence feature weighting using accumulated TP/SL evidence.

    Does NOT change Smart Money Concepts strategy rules — only statistical priors.
    """

    def record_outcome(
        self,
        fingerprint_bits: str,
        outcome: str,
        *,
        learning_strength: float = 1.0,
    ) -> None:
        features = bits_to_features(fingerprint_bits)
        now = _utc_now()
        outcome = normalize_outcome(outcome)
        # Weak reviews contribute less — never learn blindly from a single noisy case.
        strength = max(0.0, min(1.0, learning_strength))
        if is_neutral(outcome) or strength < 0.2:
            # Break-even / weak cases: stamp meta only — no win/loss counters.
            with connect() as conn:
                conn.execute(
                    """
                    INSERT INTO learning_meta (meta_key, meta_value) VALUES ('last_learning_update', ?)
                    ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                    """,
                    (now,),
                )
                conn.commit()
            return

        with connect() as conn:
            for key, active in features.items():
                if not active:
                    continue
                conn.execute(
                    """
                    INSERT INTO feature_stats (feature_key, wins, losses, last_updated)
                    VALUES (?, 0, 0, ?)
                    ON CONFLICT(feature_key) DO NOTHING
                    """,
                    (key, now),
                )
                # Fractional learning via probabilistic increment when strength < 1
                # (keep integer counters; apply only when strength passes threshold draw).
                apply = strength >= 0.55 or (strength >= 0.35 and is_win(outcome))
                if not apply:
                    continue
                if is_win(outcome):
                    conn.execute(
                        "UPDATE feature_stats SET wins = wins + 1, last_updated = ? WHERE feature_key = ?",
                        (now, key),
                    )
                elif is_loss(outcome):
                    conn.execute(
                        "UPDATE feature_stats SET losses = losses + 1, last_updated = ? WHERE feature_key = ?",
                        (now, key),
                    )
            conn.execute(
                """
                INSERT INTO learning_meta (meta_key, meta_value) VALUES ('last_learning_update', ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                """,
                (now,),
            )
            conn.commit()

        if strength >= 0.55:
            self._maybe_update_weights()

    def _maybe_update_weights(self) -> None:
        """
        Map SMC feature performance lightly onto confidence scorecard weights.
        Requires meaningful sample counts — single trades have near-zero influence.
        """
        feature_to_weight = {
            "trend_alignment": "htf_4h_alignment",
            "bos": "market_structure",
            "choch": "market_structure",
            "higher_highs": "market_structure",
            "higher_lows": "market_structure",
            "lower_highs": "market_structure",
            "lower_lows": "market_structure",
            "liquidity_sweep": "liquidity",
            "equal_highs": "liquidity",
            "equal_lows": "liquidity",
            "bullish_order_block": "order_block",
            "bearish_order_block": "order_block",
            "bullish_fvg": "fair_value_gap",
            "bearish_fvg": "fair_value_gap",
        }

        with connect() as conn:
            rows = conn.execute("SELECT feature_key, wins, losses FROM feature_stats").fetchall()
            current = {
                r["weight_key"]: float(r["weight_value"])
                for r in conn.execute("SELECT weight_key, weight_value FROM learning_weights")
            }
            for key, default in WEIGHTS.items():
                current.setdefault(key, default)

            # Aggregate evidence per weight bucket.
            bucket_scores: dict[str, list[float]] = {k: [] for k in WEIGHTS}
            for row in rows:
                fkey = row["feature_key"]
                wins = int(row["wins"])
                losses = int(row["losses"])
                total = wins + losses
                if total < MIN_SAMPLES_FOR_FEATURE_INFLUENCE:
                    continue
                win_rate = wins / total
                # Map win rate to [-1, 1] centered at 0.5
                signal = (win_rate - 0.5) * 2.0
                # Shrink by sample size toward 0 until MIN_SAMPLES_FOR_WEIGHT_UPDATE.
                shrink = min(1.0, total / float(MIN_SAMPLES_FOR_WEIGHT_UPDATE))
                weight_key = feature_to_weight.get(fkey)
                if weight_key:
                    bucket_scores[weight_key].append(signal * shrink)

            if not any(bucket_scores.values()):
                return

            adjusted = dict(current)
            for key, signals in bucket_scores.items():
                if not signals:
                    continue
                avg_signal = sum(signals) / len(signals)
                delta = max(-MAX_WEIGHT_DELTA, min(MAX_WEIGHT_DELTA, avg_signal * MAX_WEIGHT_DELTA))
                adjusted[key] = max(0.02, current.get(key, WEIGHTS[key]) + delta)

            # Renormalize to sum 1.0 — strategy structure preserved, only relative emphasis moves.
            total_w = sum(adjusted[k] for k in WEIGHTS)
            if total_w <= 0:
                return
            now = _utc_now()
            for key in WEIGHTS:
                value = adjusted[key] / total_w
                conn.execute(
                    """
                    INSERT INTO learning_weights (weight_key, weight_value, sample_count, last_updated)
                    VALUES (?, ?, 1, ?)
                    ON CONFLICT(weight_key) DO UPDATE SET
                        weight_value = excluded.weight_value,
                        sample_count = learning_weights.sample_count + 1,
                        last_updated = excluded.last_updated
                    """,
                    (key, value, now),
                )
            conn.execute(
                """
                INSERT INTO learning_meta (meta_key, meta_value) VALUES ('last_learning_update', ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                """,
                (now,),
            )
            conn.commit()

    def get_adaptive_weights(self) -> dict[str, float]:
        with connect() as conn:
            rows = conn.execute("SELECT weight_key, weight_value FROM learning_weights").fetchall()
        weights = {r["weight_key"]: float(r["weight_value"]) for r in rows}
        if not weights:
            return dict(WEIGHTS)
        # Ensure all keys exist and renormalize.
        for key, value in WEIGHTS.items():
            weights.setdefault(key, value)
        total = sum(weights[k] for k in WEIGHTS)
        if total <= 0:
            return dict(WEIGHTS)
        return {k: weights[k] / total for k in WEIGHTS}

    def feature_performance(self) -> list[dict]:
        with connect() as conn:
            rows = conn.execute(
                "SELECT feature_key, wins, losses, last_updated FROM feature_stats ORDER BY wins + losses DESC"
            ).fetchall()
        results = []
        for row in rows:
            wins = int(row["wins"])
            losses = int(row["losses"])
            total = wins + losses
            results.append(
                {
                    "feature": row["feature_key"],
                    "wins": wins,
                    "losses": losses,
                    "total": total,
                    "win_rate": round(wins / total * 100, 2) if total else None,
                    "last_updated": row["last_updated"],
                }
            )
        return results
