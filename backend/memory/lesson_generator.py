"""Advanced lesson generator from post-trade reviews."""

from __future__ import annotations

from memory.review_engine import TradeReview
from models.decision_schemas import TradeDecision


class LessonGenerator:
    def generate(
        self,
        decision: TradeDecision,
        outcome: str,
        review: TradeReview | None = None,
    ) -> str:
        if review is not None:
            return self._from_review(decision, outcome, review)
        return self._legacy(decision, outcome)

    def generate_lessons(
        self,
        decision: TradeDecision,
        outcome: str,
        review: TradeReview | None = None,
    ) -> list[str]:
        lessons: list[str] = []
        h4, h1, m15 = decision.analysis_4h, decision.analysis_1h, decision.analysis_15m
        won = outcome == "TAKE_PROFIT"

        if won and h4.trend == h1.trend and (m15.liquidity_sweep or h1.liquidity_sweep):
            if decision.overall_bias == "BUY" and (m15.bullish_order_block or h1.bullish_order_block):
                lessons.append(
                    "Bullish Order Blocks formed after liquidity sweeps have produced higher win rates."
                )
            if decision.overall_bias == "SELL" and (m15.bearish_order_block or h1.bearish_order_block):
                lessons.append(
                    "Bearish Order Blocks formed after liquidity sweeps have produced higher win rates."
                )

        if not won and h4.trend != h1.trend:
            lessons.append("Counter-trend trades without 4H alignment frequently fail.")

        if not won and m15.fair_value_gap and not (m15.bos or m15.choch or m15.liquidity_sweep):
            lessons.append("Fair Value Gap alone is not sufficient for entry.")

        if review:
            if review.scorecard.entry_quality < 60:
                lessons.append("Premature entries without clear 15M confirmation reduce expectancy.")
            if review.scorecard.stop_loss_placement < 60:
                lessons.append("Stops that ignore true invalidation levels get hunted more often.")
            if review.grade in {"A+", "A"} and won:
                lessons.append(
                    "High-grade top-down alignment with liquidity + structure confirmation remains the edge."
                )
            if decision.overall_bias == "NO TRADE":
                lessons.append("Passing on weak setups is a successful professional decision.")

        if not lessons:
            lessons.append(self.generate(decision, outcome, review))
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique: list[str] = []
        for lesson in lessons:
            if lesson not in seen:
                seen.add(lesson)
                unique.append(lesson)
        return unique[:5]

    def _from_review(self, decision: TradeDecision, outcome: str, review: TradeReview) -> str:
        lessons = self.generate_lessons(decision, outcome, review)
        return lessons[0]

    def _legacy(self, decision: TradeDecision, outcome: str) -> str:
        h4 = decision.analysis_4h
        h1 = decision.analysis_1h
        m15 = decision.analysis_15m
        direction = decision.overall_bias

        if outcome == "TAKE_PROFIT":
            points: list[str] = []
            if h4.trend == h1.trend and h4.trend in {"Bullish", "Bearish"}:
                points.append("Strong higher timeframe alignment.")
            if h1.liquidity_sweep or m15.liquidity_sweep:
                points.append("Liquidity sweep confirmed.")
            if direction == "BUY" and (h1.bullish_order_block or m15.bullish_order_block):
                points.append("Fresh bullish order block respected.")
            if direction == "SELL" and (h1.bearish_order_block or m15.bearish_order_block):
                points.append("Fresh bearish order block respected.")
            if not points:
                points.append("Setup followed top-down SMC alignment through to target.")
            return " ".join(points[:4])

        points = []
        if h4.trend != h1.trend:
            points.append("Higher timeframe disagreement weakened the thesis.")
        if direction == "BUY" and h4.trend != "Bullish":
            points.append("Counter-trend entry relative to 4H.")
        if not m15.bos and not m15.choch:
            points.append("Weak BOS / CHOCH confirmation.")
        if not points:
            points.append("Invalidation occurred despite apparent alignment — treat as variance.")
        return " ".join(points[:4])
