"""Fast similarity search over permanent trade memory."""

from __future__ import annotations

from dataclasses import dataclass

from memory.database import connect
from memory.feature_fingerprint import FEATURE_KEYS
from memory.secure_fields import unseal_text


@dataclass
class SimilarTrade:
    trade_id: str
    pair: str
    direction: str
    outcome: str
    confidence: float
    similarity: float
    fingerprint_bits: str
    lesson: str | None


@dataclass
class SimilarityReport:
    query_bits: str
    similar: list[SimilarTrade]
    total_compared: int
    tp_count: int
    sl_count: int
    win_rate: float | None
    min_similarity: float


def hamming_similarity(a: str, b: str) -> float:
    n = max(len(a), len(b), 1)
    a = a.ljust(n, "0")
    b = b.ljust(n, "0")
    matches = sum(1 for x, y in zip(a, b) if x == y)
    return matches / n


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard over active feature bits."""
    a_set = {i for i, bit in enumerate(a) if bit == "1"}
    b_set = {i for i, bit in enumerate(b) if bit == "1"}
    if not a_set and not b_set:
        return 1.0
    union = a_set | b_set
    if not union:
        return 0.0
    return len(a_set & b_set) / len(union)


def combined_similarity(a: str, b: str) -> float:
    # Blend Hamming (stable) + Jaccard (feature overlap emphasis).
    return 0.45 * hamming_similarity(a, b) + 0.55 * jaccard_similarity(a, b)


class SimilarityEngine:
    def find_similar(
        self,
        query_bits: str,
        *,
        direction: str | None = None,
        pair: str | None = None,
        min_similarity: float = 0.72,
        limit: int = 500,
        closed_only: bool = True,
    ) -> SimilarityReport:
        clauses = ["fingerprint_bits IS NOT NULL"]
        params: list[object] = []

        if closed_only:
            clauses.append("outcome IN ('TAKE_PROFIT', 'STOP_LOSS')")
        if direction and direction in {"BUY", "SELL"}:
            clauses.append("direction = ?")
            params.append(direction)
        if pair and pair != "Unknown":
            # Soft prefer same pair but do not require — fetch broader set then rank.
            pass

        where = " AND ".join(clauses)
        # Prefer same-pair rows first (indexed), then fill with broader history.
        rows = []
        with connect() as conn:
            if pair and pair != "Unknown":
                pair_sql = f"""
                    SELECT trade_id, pair, direction, outcome, confidence, fingerprint_bits, lesson
                    FROM memories
                    WHERE {where} AND pair = ?
                    ORDER BY timestamp DESC
                    LIMIT 1500
                """
                rows.extend(conn.execute(pair_sql, [*params, pair]).fetchall())
            broad_sql = f"""
                SELECT trade_id, pair, direction, outcome, confidence, fingerprint_bits, lesson
                FROM memories
                WHERE {where}
                ORDER BY timestamp DESC
                LIMIT 2500
            """
            seen = {r["trade_id"] for r in rows}
            for row in conn.execute(broad_sql, params).fetchall():
                if row["trade_id"] in seen:
                    continue
                rows.append(row)
                if len(rows) >= 4000:
                    break

        similar: list[SimilarTrade] = []
        total = 0
        for row in rows:
            total += 1
            score = combined_similarity(query_bits, row["fingerprint_bits"] or "")
            # Same-pair bonus (small).
            if pair and row["pair"] == pair:
                score = min(1.0, score + 0.03)
            if score < min_similarity:
                continue
            similar.append(
                SimilarTrade(
                    trade_id=row["trade_id"],
                    pair=row["pair"],
                    direction=row["direction"],
                    outcome=row["outcome"],
                    confidence=float(row["confidence"] or 0),
                    similarity=round(score, 4),
                    fingerprint_bits=row["fingerprint_bits"],
                    lesson=unseal_text(row["lesson"]),
                )
            )

        similar.sort(key=lambda item: item.similarity, reverse=True)
        similar = similar[:limit]
        tp = sum(1 for s in similar if s.outcome == "TAKE_PROFIT")
        sl = sum(1 for s in similar if s.outcome == "STOP_LOSS")
        closed = tp + sl
        win_rate = (tp / closed * 100.0) if closed else None

        return SimilarityReport(
            query_bits=query_bits,
            similar=similar,
            total_compared=total,
            tp_count=tp,
            sl_count=sl,
            win_rate=round(win_rate, 2) if win_rate is not None else None,
            min_similarity=min_similarity,
        )


def describe_top_features(bits: str, top_n: int = 5) -> list[str]:
    active = [FEATURE_KEYS[i] for i, bit in enumerate(bits) if bit == "1"]
    return active[:top_n]
