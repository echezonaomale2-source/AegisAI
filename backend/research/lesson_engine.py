"""Lesson engine — concise permanent lessons from each review."""

from __future__ import annotations

from models.schemas import utc_now_iso
from memory.database import connect
from research.database import init_research_db
from research.models import ReviewReport

init_research_db()


class LessonEngine:
    def from_review(self, report: ReviewReport) -> list[str]:
        lessons: list[str] = []
        if report.htf_bias_correct:
            lessons.append("Strong higher-timeframe alignment improved decision quality.")
        else:
            lessons.append("Weak or conflicting higher-timeframe bias reduced analysis quality.")

        if report.should_have_been_no_trade:
            lessons.append("Insufficient confirmation — NO TRADE would have been more appropriate.")

        if report.confidence_appropriate is False:
            lessons.append("Confidence was too high relative to historical evidence.")

        if report.liquidity_identified_correctly and not report.m15_confirmation_valid:
            lessons.append("Liquidity sweeps without additional confirmation were unreliable.")

        if report.m15_confirmation_valid is False and report.outcome in {"STOP_LOSS", "SL"}:
            lessons.append("Counter-trend or weakly confirmed entries produced inconsistent outcomes.")

        if report.order_block_respected and report.decision_quality in {"Excellent", "Good"}:
            lessons.append("Respected order-block context supported higher analysis quality.")

        if report.fvg_meaningful is False:
            lessons.append("FVG contributed little — avoid overweighting weak gaps.")

        # Deduplicate, keep concise
        out: list[str] = []
        for lesson in lessons:
            if lesson not in out:
                out.append(lesson)
        report.lessons = out[:6]
        return report.lessons

    def store(self, trade_id: str, lessons: list[str], *, category: str = "review") -> None:
        now = utc_now_iso()
        with connect() as conn:
            for text in lessons:
                conn.execute(
                    """
                    INSERT INTO research_lessons (trade_id, lesson_text, category, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (trade_id, text, category, now),
                )
            conn.commit()

    def recent(self, limit: int = 10) -> list[str]:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT lesson_text FROM research_lessons
                ORDER BY created_at DESC, lesson_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [r["lesson_text"] for r in rows]
