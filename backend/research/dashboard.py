"""Research dashboard aggregates — indexed queries for large history."""

from __future__ import annotations

from collections import Counter

from memory.database import connect
from memory.learning_engine import LearningEngine
from memory.memory_repository import MemoryRepository
from memory.pattern_engine import PatternEngine
from research.confidence_calibration import ConfidenceCalibrationEngine
from research.database import init_research_db
from research.lesson_engine import LessonEngine
from research.models import ResearchDashboard
from research.pattern_library import PatternLibrary

init_research_db()


class ResearchDashboardService:
    def __init__(self) -> None:
        self.calibration = ConfidenceCalibrationEngine()
        self.patterns = PatternLibrary()
        self.lessons = LessonEngine()
        self.memory_patterns = PatternEngine()
        self.learning = LearningEngine()
        self.memory_repo = MemoryRepository()

    def build(self) -> ResearchDashboard:
        with connect() as conn:
            total = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
            awaiting = conn.execute(
                """
                SELECT COUNT(*) AS c FROM memories
                WHERE outcome IS NULL AND final_decision IN ('BUY', 'SELL')
                """
            ).fetchone()["c"]
            reviews = conn.execute(
                "SELECT COUNT(*) AS c FROM research_reviews"
            ).fetchone()["c"]

            # Fallback awaiting if status column used
            if awaiting == 0:
                awaiting = conn.execute(
                    """
                    SELECT COUNT(*) AS c FROM memories
                    WHERE status LIKE '%Waiting%' OR (outcome IS NULL AND final_decision != 'NO TRADE')
                    """
                ).fetchone()["c"]

            quality_rows = conn.execute(
                "SELECT decision_quality, COUNT(*) AS c FROM research_reviews GROUP BY decision_quality"
            ).fetchall()
            quality_dist = {r["decision_quality"]: r["c"] for r in quality_rows}

            top_loss = conn.execute(
                """
                SELECT reason_key FROM research_loss_reasons
                ORDER BY count DESC LIMIT 1
                """
            ).fetchone()
            top_no_trade = conn.execute(
                """
                SELECT reason_key FROM research_no_trade_reasons
                ORDER BY count DESC LIMIT 1
                """
            ).fetchone()

            # Derive NO TRADE reasons from memories if counter empty
            if top_no_trade is None:
                no_trade_rows = conn.execute(
                    """
                    SELECT explanation FROM memories
                    WHERE final_decision = 'NO TRADE'
                    ORDER BY timestamp DESC LIMIT 200
                    """
                ).fetchall()
                reasons = Counter()
                for row in no_trade_rows:
                    key = _summarize_no_trade(row["explanation"] or "")
                    reasons[key] += 1
                top_no_trade_reason = reasons.most_common(1)[0][0] if reasons else None
            else:
                top_no_trade_reason = top_no_trade["reason_key"]

            if top_loss is None:
                loss_rows = conn.execute(
                    """
                    SELECT lesson, lessons_json, explanation FROM memories
                    WHERE outcome = 'STOP_LOSS'
                    ORDER BY closed_at DESC LIMIT 200
                    """
                ).fetchall()
                reasons = Counter()
                for row in loss_rows:
                    text = row["lesson"] or row["explanation"] or "Unspecified weakness"
                    reasons[_summarize_loss(text)] += 1
                top_loss_reason = reasons.most_common(1)[0][0] if reasons else None
            else:
                top_loss_reason = top_loss["reason_key"]

        closed = self.memory_repo.closed_stats()
        feature_perf = self.learning.feature_performance()[:6]
        adaptive = self.learning.get_adaptive_weights()
        mem_top = self.memory_patterns.top_patterns(5)

        return ResearchDashboard(
            total_analyses=int(total),
            trades_awaiting_results=int(awaiting),
            completed_reviews=int(reviews),
            current_confidence_calibration=self.calibration.state(),
            most_reliable_feature_combination=self.patterns.most_reliable(),
            least_reliable_feature_combination=self.patterns.least_reliable(),
            most_common_reason_for_losing_trades=top_loss_reason,
            most_common_reason_for_no_trade=top_no_trade_reason,
            recent_lessons=self.lessons.recent(8),
            decision_quality_distribution=quality_dist,
            top_patterns=self.patterns.top_patterns(6),
            memory_snapshot={
                "total_trades_stored": closed.get("total_trades_stored"),
                "winning_trades": closed.get("winning_trades"),
                "losing_trades": closed.get("losing_trades"),
                "waiting_trades": closed.get("waiting_trades"),
                "estimated_win_rate": closed.get("estimated_win_rate"),
                "most_successful_pair": closed.get("most_successful_pair"),
                "last_learning_update": closed.get("last_learning_update"),
                "top_memory_patterns": mem_top,
            },
            learning_snapshot={
                "adaptive_weights": adaptive,
                "feature_reliability": feature_perf,
                "recent_lessons": self.lessons.recent(5),
            },
            notes=[
                "Decision quality is independent of win/loss.",
                "Calibration adjusts gradually — never from a single trade.",
                "Learning summaries update incrementally; history is never rewritten.",
            ],
        )


def _summarize_no_trade(explanation: str) -> str:
    text = explanation.lower()
    if "uncertainty" in text or "quality" in text:
        return "Image uncertainty / quality"
    if "conflict" in text or "margin" in text:
        return "Conflicting evidence"
    if "confidence" in text:
        return "Confidence below threshold"
    if "liquidity" in text:
        return "Unclear liquidity"
    if "structure" in text:
        return "Missing market structure"
    if "risk" in text or "reward" in text or "rr" in text:
        return "Insufficient risk/reward"
    if "self-check" in text:
        return "Failed self-check"
    return "Insufficient evidence"


def _summarize_loss(text: str) -> str:
    low = text.lower()
    if "liquidity" in low:
        return "Liquidity misread"
    if "order block" in low or "ob" in low:
        return "Order block failure"
    if "confirmation" in low or "15m" in low:
        return "Weak LTF confirmation"
    if "confidence" in low:
        return "Overconfidence"
    if "counter" in low or "trend" in low:
        return "Counter-trend entry"
    return "Setup invalidated"
