from pathlib import Path

from fastapi.testclient import TestClient

from main import app
from tests.conftest import render_synthetic_chart

client = TestClient(app)


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_chart_endpoint(tmp_path: Path):
    path = render_synthetic_chart(tmp_path / "api_chart.png")
    with path.open("rb") as handle:
        response = client.post(
            "/api/analyze/chart",
            files={"chart": ("chart.png", handle, "image/png")},
            data={"expected_timeframe": "4H"},
        )
    assert response.status_code == 200
    payload = response.json()
    assert "trend" in payload
    assert "confidence" in payload
    assert "confidence_breakdown" in payload


def test_analyze_multi_endpoint(tmp_path: Path):
    p4 = render_synthetic_chart(tmp_path / "m4.png")
    p1 = render_synthetic_chart(tmp_path / "m1.png")
    p15 = render_synthetic_chart(tmp_path / "m15.png")
    with p4.open("rb") as f4, p1.open("rb") as f1, p15.open("rb") as f15:
        response = client.post(
            "/api/analyze/multi",
            files={
                "chart_4h": ("4h.png", f4, "image/png"),
                "chart_1h": ("1h.png", f1, "image/png"),
                "chart_15m": ("15m.png", f15, "image/png"),
            },
        )
    assert response.status_code == 200
    payload = response.json()
    assert "chart_4h" in payload
    assert "chart_1h" in payload
    assert "chart_15m" in payload
    assert payload["chart_4h"]["status"] in {"ok", "error"}
