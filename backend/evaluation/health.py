"""Module health grading — objective scores from metrics."""

from __future__ import annotations

from models.schemas import utc_now_iso
from evaluation.models import (
    CalibrationMetrics,
    DecisionMetrics,
    EvaluationReport,
    FeatureMetrics,
    HealthGrade,
    KnowledgeMetrics,
    LearningMetrics,
    ModuleHealth,
    SystemHealthReport,
    TradeReviewMetrics,
    VisionMetrics,
)


def _grade(score: float) -> HealthGrade:
    if score >= 85:
        return "Excellent"
    if score >= 70:
        return "Good"
    if score >= 55:
        return "Improving"
    if score >= 40:
        return "Needs Review"
    if score > 0:
        return "Critical"
    return "Unknown"


class HealthReporter:
    def build(self, report: EvaluationReport) -> SystemHealthReport:
        modules = [
            self._vision(report.vision),
            self._knowledge(report.knowledge),
            self._features(report.features),
            self._decision(report.decisions),
            self._learning(report.learning),
            self._calibration(report.calibration),
            self._reviews(report.trade_reviews),
        ]
        known = [m for m in modules if m.grade != "Unknown"]
        overall = sum(m.score for m in known) / len(known) if known else 0.0
        return SystemHealthReport(
            overall_grade=_grade(overall),
            overall_score=round(overall, 1),
            modules=modules,
            generated_at=utc_now_iso(),
        )

    def _vision(self, m: VisionMetrics) -> ModuleHealth:
        if m.images_accepted + m.images_rejected == 0:
            return ModuleHealth(module="Vision Engine", grade="Unknown", score=0, notes=["No samples yet."])
        score = m.accept_rate or 0.0
        if m.avg_detection_confidence is not None:
            score = 0.6 * score + 0.4 * m.avg_detection_confidence
        notes = [f"Accept rate {m.accept_rate}%", f"Unknown detections {m.unknown_detections}"]
        return ModuleHealth(module="Vision Engine", grade=_grade(score), score=round(score, 1), notes=notes)

    def _knowledge(self, m: KnowledgeMetrics) -> ModuleHealth:
        total = m.concepts_validated + m.concepts_rejected
        if total == 0:
            return ModuleHealth(module="Knowledge Engine", grade="Unknown", score=0, notes=["No validations yet."])
        # Higher validation pass rate is healthier (with some rejections expected)
        pass_rate = 100.0 * m.concepts_validated / total
        score = min(100.0, pass_rate)
        return ModuleHealth(
            module="Knowledge Engine",
            grade=_grade(score),
            score=round(score, 1),
            notes=[f"Validated {m.concepts_validated}, rejected {m.concepts_rejected}"],
        )

    def _features(self, m: FeatureMetrics) -> ModuleHealth:
        rates = [
            x
            for x in [
                m.trend_detection_rate,
                m.bos_detection_rate,
                m.liquidity_detection_rate,
                m.order_block_detection_rate,
            ]
            if x is not None
        ]
        if not rates:
            return ModuleHealth(module="Feature Extraction", grade="Unknown", score=0)
        # Balanced detection without extreme unknown rate
        score = min(100.0, sum(rates) / len(rates))
        if m.unknown_rate is not None:
            score = max(0.0, score - min(30.0, m.unknown_rate * 0.3))
        return ModuleHealth(
            module="Feature Extraction",
            grade=_grade(score),
            score=round(min(100.0, score), 1),
            notes=[f"Unknown rate {m.unknown_rate}%"],
        )

    def _decision(self, m: DecisionMetrics) -> ModuleHealth:
        if m.total_decisions == 0:
            return ModuleHealth(module="Decision Engine", grade="Unknown", score=0)
        # Healthy if NO TRADE is used when needed and confidence is tracked
        no_trade_share = 100.0 * m.no_trade_recommendations / m.total_decisions
        conf = m.average_confidence or 50.0
        # Prefer some NO TRADE discipline (10–70%) plus solid confidence tracking
        discipline = 100.0 - abs(no_trade_share - 40.0)
        score = 0.5 * conf + 0.5 * max(0.0, discipline)
        score = min(100.0, max(0.0, score))
        return ModuleHealth(
            module="Decision Engine",
            grade=_grade(score),
            score=round(score, 1),
            notes=[
                f"BUY {m.buy_recommendations} / SELL {m.sell_recommendations} / NO TRADE {m.no_trade_recommendations}",
                f"Avg confidence {m.average_confidence}",
            ],
        )

    def _learning(self, m: LearningMetrics) -> ModuleHealth:
        if m.memory_growth == 0 and m.lessons_generated == 0:
            return ModuleHealth(module="Learning Engine", grade="Unknown", score=0, notes=["No learning activity."])
        score = min(
            100.0,
            20
            + min(40, m.lessons_generated * 2)
            + min(20, m.pattern_statistics_updated)
            + min(20, m.confidence_adjustments_made),
        )
        grade = _grade(score)
        if m.lessons_generated == 0 and m.memory_growth > 5:
            grade = "Needs Review"
            score = min(score, 45)
        return ModuleHealth(
            module="Learning Engine",
            grade=grade,
            score=round(score, 1),
            notes=[f"Memories {m.memory_growth}, lessons {m.lessons_generated}"],
        )

    def _calibration(self, m: CalibrationMetrics) -> ModuleHealth:
        if m.sample_count < 10:
            return ModuleHealth(
                module="Confidence Calibration",
                grade="Improving",
                score=50.0,
                notes=m.notes or ["Warming up."],
            )
        # Lower absolute gap is better
        gap_penalty = min(50.0, abs(m.global_gap) * 2)
        score = max(0.0, 100.0 - gap_penalty)
        return ModuleHealth(
            module="Confidence Calibration",
            grade=_grade(score),
            score=round(score, 1),
            notes=m.notes + [f"Gap {m.global_gap}%", f"Factor {m.adjustment_factor}"],
        )

    def _reviews(self, m: TradeReviewMetrics) -> ModuleHealth:
        if m.completed_reviews == 0:
            return ModuleHealth(module="Trade Review", grade="Unknown", score=0)
        score = m.average_review_score or 50.0
        return ModuleHealth(
            module="Trade Review",
            grade=_grade(score),
            score=round(score, 1),
            notes=[f"Reviews {m.completed_reviews}", f"Avg score {m.average_review_score}"],
        )
