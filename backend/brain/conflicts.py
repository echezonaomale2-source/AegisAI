"""Conflict detection across timeframes and evidence sides."""

from __future__ import annotations

from brain.models import ConflictReport, EngineBundle


class ConflictDetector:
    def detect(self, bundle: EngineBundle) -> ConflictReport:
        conflicts: list[str] = []
        htf_disagreement = False

        vision = bundle.vision_summaries
        t4 = (vision.get("4H") or {}).get("trend", "Unknown")
        t1 = (vision.get("1H") or {}).get("trend", "Unknown")
        t15 = (vision.get("15M") or {}).get("trend", "Unknown")

        if t4 in {"Bullish", "Bearish"} and t1 in {"Bullish", "Bearish"} and t4 != t1:
            htf_disagreement = True
            conflicts.append(f"4H trend {t4} conflicts with 1H trend {t1}.")

        if t4 in {"Bullish", "Bearish"} and t15 in {"Bullish", "Bearish"} and t4 != t15:
            conflicts.append(f"4H trend {t4} conflicts with 15M trend {t15}.")

        reasoning = bundle.reasoning or {}
        buy = float(reasoning.get("buy_evidence_score", 0) or 0)
        sell = float(reasoning.get("sell_evidence_score", 0) or 0)
        if buy > 40 and sell > 40 and abs(buy - sell) < 15:
            conflicts.append(
                f"Evidence roughly balanced (BUY {buy:.0f} vs SELL {sell:.0f})."
            )

        for item in reasoning.get("conflicts_summary") or []:
            conflicts.append(str(item))

        if htf_disagreement:
            severity = "high"
        elif len(conflicts) >= 3:
            severity = "high"
        elif conflicts:
            severity = "medium" if len(conflicts) >= 2 else "low"
        else:
            severity = "none"

        return ConflictReport(
            has_conflicts=bool(conflicts),
            htf_disagreement=htf_disagreement,
            conflicts=conflicts,
            severity=severity,  # type: ignore[arg-type]
        )
