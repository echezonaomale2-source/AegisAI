"""
AegisAI Evaluation & Validation Framework (Phase 9).

Objective measurement of every module. Improvements require evidence.
"""

__all__ = ["EvaluationEngine", "EvaluationDashboardService"]


def __getattr__(name: str):
    if name == "EvaluationEngine":
        from evaluation.engine import EvaluationEngine

        return EvaluationEngine
    if name == "EvaluationDashboardService":
        from evaluation.dashboard import EvaluationDashboardService

        return EvaluationDashboardService
    raise AttributeError(name)
