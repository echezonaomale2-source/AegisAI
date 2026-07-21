"""Pattern database — permanent statistics for named SMC feature combinations."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from memory.database import connect
from memory.feature_fingerprint import FEATURE_KEYS, bits_to_features


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


PATTERN_CORE_KEYS = [
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
    "premium",
    "discount",
    "direction_buy",
    "direction_sell",
]


def pattern_label_from_bits(bits: str) -> str:
    features = bits_to_features(bits)
    parts: list[str] = []
    if features.get("direction_buy"):
        parts.append("BUY")
    if features.get("direction_sell"):
        parts.append("SELL")
    if features.get("trend_alignment"):
        parts.append("HTF Aligned")
    if features.get("liquidity_sweep"):
        parts.append("Liquidity Sweep")
    if features.get("bos"):
        parts.append("BOS")
    if features.get("choch"):
        parts.append("CHOCH")
    if features.get("bullish_order_block"):
        parts.append("Bullish OB")
    if features.get("bearish_order_block"):
        parts.append("Bearish OB")
    if features.get("bullish_fvg"):
        parts.append("Bullish FVG")
    if features.get("bearish_fvg"):
        parts.append("Bearish FVG")
    if features.get("demand_zone"):
        parts.append("Demand")
    if features.get("supply_zone"):
        parts.append("Supply")
    if features.get("discount"):
        parts.append("Discount")
    if features.get("premium"):
        parts.append("Premium")
    return " + ".join(parts) if parts else "Unspecified Pattern"


def pattern_key_from_bits(bits: str) -> str:
    features = bits_to_features(bits)
    flags = "".join("1" if features.get(k) else "0" for k in PATTERN_CORE_KEYS)
    return flags


class PatternEngine:
    def ensure_schema(self, conn) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS patterns (
                pattern_key TEXT PRIMARY KEY,
                pattern_label TEXT NOT NULL,
                features_json TEXT NOT NULL,
                trades INTEGER NOT NULL DEFAULT 0,
                wins INTEGER NOT NULL DEFAULT 0,
                losses INTEGER NOT NULL DEFAULT 0,
                rr_sum REAL NOT NULL DEFAULT 0,
                confidence_sum REAL NOT NULL DEFAULT 0,
                last_updated TEXT
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_patterns_wins ON patterns(wins DESC)"
        )

    def record(
        self,
        fingerprint_bits: str,
        *,
        outcome: str,
        risk_reward: float | None,
        confidence: float,
    ) -> dict:
        key = pattern_key_from_bits(fingerprint_bits)
        label = pattern_label_from_bits(fingerprint_bits)
        features = {k: bits_to_features(fingerprint_bits).get(k, False) for k in PATTERN_CORE_KEYS}
        now = _utc_now()
        rr = float(risk_reward or 0.0)
        won = outcome == "TAKE_PROFIT"
        lost = outcome == "STOP_LOSS"
        # BREAK_EVEN: count occurrence but neither win nor loss

        with connect() as conn:
            self.ensure_schema(conn)
            conn.execute(
                """
                INSERT INTO patterns (
                    pattern_key, pattern_label, features_json, trades, wins, losses,
                    rr_sum, confidence_sum, last_updated
                ) VALUES (?, ?, ?, 0, 0, 0, 0, 0, ?)
                ON CONFLICT(pattern_key) DO NOTHING
                """,
                (key, label, json.dumps(features), now),
            )
            conn.execute(
                f"""
                UPDATE patterns
                SET trades = trades + 1,
                    wins = wins + ?,
                    losses = losses + ?,
                    rr_sum = rr_sum + ?,
                    confidence_sum = confidence_sum + ?,
                    pattern_label = ?,
                    last_updated = ?
                WHERE pattern_key = ?
                """,
                (
                    1 if won else 0,
                    1 if lost else 0,
                    rr,
                    float(confidence or 0),
                    label,
                    now,
                    key,
                ),
            )
            row = conn.execute(
                "SELECT * FROM patterns WHERE pattern_key = ?",
                (key,),
            ).fetchone()
            conn.commit()

        return self._row_to_dict(row)

    def get(self, fingerprint_bits: str) -> dict | None:
        key = pattern_key_from_bits(fingerprint_bits)
        with connect() as conn:
            self.ensure_schema(conn)
            row = conn.execute(
                "SELECT * FROM patterns WHERE pattern_key = ?",
                (key,),
            ).fetchone()
        return self._row_to_dict(row) if row else None

    def top_patterns(self, limit: int = 10) -> list[dict]:
        with connect() as conn:
            self.ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT * FROM patterns
                WHERE trades > 0
                ORDER BY wins DESC, trades DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def worst_patterns(self, limit: int = 5) -> list[dict]:
        with connect() as conn:
            self.ensure_schema(conn)
            rows = conn.execute(
                """
                SELECT * FROM patterns
                WHERE trades >= 3
                ORDER BY CAST(losses AS REAL) / trades DESC, losses DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_dict(r) for r in rows]

    def _row_to_dict(self, row) -> dict:
        trades = int(row["trades"] or 0)
        wins = int(row["wins"] or 0)
        losses = int(row["losses"] or 0)
        rr_sum = float(row["rr_sum"] or 0)
        conf_sum = float(row["confidence_sum"] or 0)
        return {
            "pattern_key": row["pattern_key"],
            "pattern": row["pattern_label"],
            "features": json.loads(row["features_json"] or "{}"),
            "trades": trades,
            "wins": wins,
            "losses": losses,
            "average_rr": round(rr_sum / trades, 2) if trades else None,
            "confidence": round(conf_sum / trades, 1) if trades else None,
            "win_rate": round(wins / trades * 100, 2) if trades else None,
            "last_updated": row["last_updated"],
        }
