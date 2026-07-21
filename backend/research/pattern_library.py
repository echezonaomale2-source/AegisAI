"""Pattern library — incremental statistics for feature combinations."""

from __future__ import annotations

import hashlib
import json

from models.schemas import utc_now_iso
from memory.database import connect
from research.database import init_research_db
from research.models import PatternRecord

init_research_db()


class PatternLibrary:
    def pattern_id(self, features: list[str]) -> str:
        normalized = sorted({f.strip().lower() for f in features if f})
        raw = "|".join(normalized) or "empty"
        return hashlib.sha1(raw.encode()).hexdigest()[:16]

    def get(self, features: list[str]) -> PatternRecord | None:
        pid = self.pattern_id(features)
        with connect() as conn:
            row = conn.execute(
                "SELECT * FROM research_patterns WHERE pattern_id = ?", (pid,)
            ).fetchone()
        if row is None:
            return None
        return self._row_to_record(row)

    def record_outcome(
        self,
        features: list[str],
        *,
        outcome: str | None,
        confidence: float,
        risk_reward: float | None = None,
        holding_hours: float | None = None,
        was_no_trade: bool = False,
    ) -> PatternRecord:
        """Incrementally update pattern stats — never overwrite historical counters downward."""
        normalized = sorted({f.strip().lower() for f in features if f})
        pid = self.pattern_id(normalized)
        now = utc_now_iso()
        win = 1 if outcome in {"TAKE_PROFIT", "TP"} else 0
        loss = 1 if outcome in {"STOP_LOSS", "SL"} else 0
        no_trade = 1 if was_no_trade else 0
        rr = float(risk_reward) if risk_reward is not None else 0.0
        hold = float(holding_hours) if holding_hours is not None else 0.0
        hold_sample = 1 if holding_hours is not None else 0

        with connect() as conn:
            conn.execute(
                """
                INSERT INTO research_patterns (
                    pattern_id, features_json, occurrences, wins, losses,
                    no_trade_recommendations, confidence_sum, rr_sum,
                    holding_hours_sum, holding_samples, last_updated
                ) VALUES (?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(pattern_id) DO UPDATE SET
                    occurrences = occurrences + 1,
                    wins = wins + excluded.wins,
                    losses = losses + excluded.losses,
                    no_trade_recommendations = no_trade_recommendations + excluded.no_trade_recommendations,
                    confidence_sum = confidence_sum + excluded.confidence_sum,
                    rr_sum = rr_sum + excluded.rr_sum,
                    holding_hours_sum = holding_hours_sum + excluded.holding_hours_sum,
                    holding_samples = holding_samples + excluded.holding_samples,
                    last_updated = excluded.last_updated
                """,
                (
                    pid,
                    json.dumps(normalized),
                    win,
                    loss,
                    no_trade,
                    float(confidence),
                    rr,
                    hold,
                    hold_sample,
                    now,
                ),
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM research_patterns WHERE pattern_id = ?", (pid,)
            ).fetchone()
        return self._row_to_record(row)

    def most_reliable(self, *, min_occurrences: int = 5) -> PatternRecord | None:
        ranked = self.top_patterns(limit=1, min_occurrences=min_occurrences)
        return ranked[0] if ranked else None

    def top_patterns(self, limit: int = 10, *, min_occurrences: int = 3) -> list[PatternRecord]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM research_patterns
                WHERE occurrences >= ? AND (wins + losses) >= 1
                ORDER BY
                    CAST(wins AS REAL) / NULLIF(wins + losses, 0) DESC,
                    occurrences DESC
                LIMIT ?
                """,
                (min_occurrences, limit),
            ).fetchall()
        return [self._row_to_record(r) for r in rows]

    def least_reliable(self, *, min_occurrences: int = 5) -> PatternRecord | None:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM research_patterns
                WHERE occurrences >= ? AND (wins + losses) >= 3
                ORDER BY
                    CAST(losses AS REAL) / NULLIF(wins + losses, 0) DESC,
                    occurrences DESC
                LIMIT 20
                """,
                (min_occurrences,),
            ).fetchall()
        records = [self._row_to_record(r) for r in rows]
        if not records:
            return None
        return min(records, key=lambda r: (r.reliability_score or 0, -r.occurrences))

    def _row_to_record(self, row) -> PatternRecord:
        features = json.loads(row["features_json"] or "[]")
        occ = int(row["occurrences"])
        wins = int(row["wins"])
        losses = int(row["losses"])
        closed = wins + losses
        avg_conf = (row["confidence_sum"] / occ) if occ else None
        avg_rr = (row["rr_sum"] / closed) if closed and row["rr_sum"] else None
        hold_n = int(row["holding_samples"] or 0)
        avg_hold = (row["holding_hours_sum"] / hold_n) if hold_n else None
        reliability = (wins / closed) if closed else None
        return PatternRecord(
            pattern_id=row["pattern_id"],
            feature_combination=features,
            occurrences=occ,
            wins=wins,
            losses=losses,
            no_trade_recommendations=int(row["no_trade_recommendations"]),
            average_confidence=round(avg_conf, 2) if avg_conf is not None else None,
            average_risk_reward=round(avg_rr, 3) if avg_rr is not None else None,
            average_holding_time_hours=round(avg_hold, 2) if avg_hold is not None else None,
            last_updated=row["last_updated"],
            reliability_score=round(reliability * 100, 2) if reliability is not None else None,
        )
