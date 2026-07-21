"""Evaluation dashboard — system health + research-aligned KPIs."""

from __future__ import annotations

from evaluation.engine import EvaluationEngine
from evaluation.models import EvaluationDashboard
from evaluation.path_logger import DecisionPathLogger
from research.dashboard import ResearchDashboardService


class EvaluationDashboardService:
    def __init__(self) -> None:
        self.eval = EvaluationEngine()
        self.research = ResearchDashboardService()
        self.paths = DecisionPathLogger()

    def build(self, *, persist_report: bool = True) -> EvaluationDashboard:
        report = self.eval.build_report(persist=persist_report)
        research = self.research.build()

        cal_quality = "Unknown"
        for mod in report.health.modules:
            if mod.module == "Confidence Calibration":
                cal_quality = mod.grade
                break

        most = research.most_reliable_feature_combination
        least = research.least_reliable_feature_combination
        most_label = (
            " + ".join(most.feature_combination) if most and most.feature_combination else None
        )
        least_label = (
            " + ".join(least.feature_combination) if least and least.feature_combination else None
        )

        no_trade = []
        if research.most_common_reason_for_no_trade:
            no_trade.append(research.most_common_reason_for_no_trade)

        return EvaluationDashboard(
            total_analyses=research.total_analyses,
            completed_reviews=research.completed_reviews,
            current_calibration_quality=cal_quality,
            most_reliable_feature=most_label,
            least_reliable_feature=least_label,
            common_no_trade_reasons=no_trade,
            recent_lessons=list(research.recent_lessons),
            overall_system_health=report.health,
            latest_report_id=report.report_id,
            decision_path_log_count=self.paths.count(),
        )
