"""Field-level at-rest helpers for Memory Engine (Fernet, enc:v1: prefix)."""

from __future__ import annotations

from typing import Any

from config.settings import settings
from core.security.encryption import PREFIX, get_encryptor

# Narrative / analysis payloads — fingerprint bits stay plaintext for similarity.
SENSITIVE_MEMORY_COLUMNS = (
    "features_json",
    "analysis_4h_json",
    "analysis_1h_json",
    "analysis_15m_json",
    "explanation",
    "lesson",
    "review_json",
    "lessons_json",
)

SENSITIVE_REVIEW_COLUMNS = (
    "scorecard_json",
    "critique_json",
    "questions_json",
    "lessons_json",
    "summary",
    "outcome_analysis_json",
)


def seal_text(value: str | None) -> str | None:
    if value is None:
        return None
    if not settings.encrypt_memory_at_rest:
        return value
    if value.startswith(PREFIX):
        return value
    return get_encryptor().encrypt_text(value)


def unseal_text(value: str | None) -> str | None:
    if value is None:
        return None
    return get_encryptor().decrypt_text(value)


def seal_json_dump(payload: Any) -> str:
    import json

    text = json.dumps(payload)
    sealed = seal_text(text)
    return sealed if sealed is not None else text


def unseal_row(row: dict[str, Any], columns: tuple[str, ...] = SENSITIVE_MEMORY_COLUMNS) -> dict[str, Any]:
    out = dict(row)
    for col in columns:
        if col in out and out[col] is not None:
            out[col] = unseal_text(out[col])
    return out
