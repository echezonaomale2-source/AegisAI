"""Performance engine — trade quality grades and process success metrics."""

from __future__ import annotations

from memory.review_engine import ReviewScorecard, grade_from_score


class PerformanceEngine:
    def classify(self, scorecard: ReviewScorecard) -> dict:
        grade = grade_from_score(scorecard.overall_analysis_quality)
        labels = {
            "A+": "Excellent",
            "A": "Very Strong",
            "B": "Good",
            "C": "Average",
            "D": "Weak",
            "F": "Avoid",
        }
        return {
            "grade": grade,
            "label": labels[grade],
            "overall": scorecard.overall_analysis_quality,
            "should_influence_learning": scorecard.overall_analysis_quality >= 55,
            "learning_strength": min(1.0, max(0.15, scorecard.overall_analysis_quality / 100.0)),
        }

    def no_trade_is_success(self, direction: str) -> bool:
        """Withholding a weak setup is a successful professional decision."""
        return direction == "NO TRADE"
