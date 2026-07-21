"""Decision quality classifier — process quality, independent of win/loss."""

from __future__ import annotations

from research.models import DecisionQuality, ResearchScorecard


class DecisionQualityClassifier:
    """
    Excellent / Good / Acceptable / Borderline / Avoid

    Based solely on analysis scorecard — never on TP/SL outcome.
    """

    def classify(self, scorecard: ResearchScorecard) -> DecisionQuality:
        score = scorecard.overall_analysis_quality
        if score >= 88:
            return "Excellent"
        if score >= 75:
            return "Good"
        if score >= 60:
            return "Acceptable"
        if score >= 45:
            return "Borderline"
        return "Avoid"
