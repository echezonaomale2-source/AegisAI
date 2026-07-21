"""Persist reason traces for debugging and review (encrypted at rest)."""

from __future__ import annotations

import json
from pathlib import Path

from brain.models import ReasonTrace
from config.settings import settings
from core.security.encryption import get_encryptor
from models.schemas import utc_now_iso


class ReasonTraceStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (
            Path(__file__).resolve().parent.parent / "storage" / "brain_traces"
        )
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, trace: ReasonTrace, *, trade_id: str | None = None) -> Path:
        name = f"{trade_id or trace.trace_id}.json"
        path = self.root / name
        payload = json.dumps(
            {
                "saved_at": utc_now_iso(),
                "trade_id": trade_id,
                "trace": trace.model_dump(mode="json"),
            },
            indent=2,
            default=str,
        )
        if settings.encrypt_memory_at_rest:
            payload = get_encryptor().encrypt_text(payload)
        path.write_text(payload, encoding="utf-8")
        return path

    def load(self, trade_id_or_trace: str) -> dict | None:
        path = self.root / f"{trade_id_or_trace}.json"
        if not path.exists():
            return None
        raw = get_encryptor().decrypt_text(path.read_text(encoding="utf-8"))
        return json.loads(raw)
