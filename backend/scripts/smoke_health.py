"""Smoke: app boots and /api/health responds."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    from fastapi.testclient import TestClient

    from main import app

    client = TestClient(app)
    root = client.get("/")
    health = client.get("/api/health")
    assert root.status_code == 200, root.text
    assert health.status_code == 200, health.text
    body = health.json()
    print("ok", body.get("status") or body)
    print("version", root.json().get("version"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
