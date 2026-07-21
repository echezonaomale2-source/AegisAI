"""Step 9 — Research Dashboard API smoke tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from main import app
from research.dashboard import ResearchDashboardService


def test_research_dashboard_build_shape() -> None:
    dash = ResearchDashboardService().build()
    payload = dash.model_dump(mode="json")
    assert "total_analyses" in payload
    assert "current_confidence_calibration" in payload
    assert "recent_lessons" in payload
    assert "top_patterns" in payload
    assert "memory_snapshot" in payload
    assert "learning_snapshot" in payload
    assert "estimated_win_rate" in payload["memory_snapshot"]
    assert "adaptive_weights" in payload["learning_snapshot"]
    assert "feature_reliability" in payload["learning_snapshot"]


def test_research_dashboard_http() -> None:
    client = TestClient(app)
    resp = client.get("/api/research/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["total_analyses"], int)
    assert "bins" in (body.get("current_confidence_calibration") or {})
    assert "memory_snapshot" in body
    assert "learning_snapshot" in body


def test_evaluation_dashboard_and_health_http() -> None:
    client = TestClient(app)
    dash = client.get("/api/evaluation/dashboard")
    assert dash.status_code == 200
    body = dash.json()
    assert "overall_system_health" in body

    health = client.get("/api/evaluation/health")
    assert health.status_code == 200
    h = health.json()
    assert "overall_grade" in h or "overall_score" in h or "modules" in h


def test_memory_stats_http() -> None:
    client = TestClient(app)
    resp = client.get("/api/memory/stats")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_trades_stored" in body or "total_memories_stored" in body


def test_learning_summary_http() -> None:
    client = TestClient(app)
    resp = client.get("/api/learning/summary")
    assert resp.status_code == 200
    assert "calibration" in resp.json()
