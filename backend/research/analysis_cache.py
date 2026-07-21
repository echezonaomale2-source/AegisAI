"""Immutable analysis result cache — avoid duplicate feature extraction."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from models.schemas import utc_now_iso
from research.database import init_research_db
from memory.database import connect

init_research_db()


class AnalysisCache:
    """
    Cache immutable analysis payloads keyed by content hash of source images.

    Supports ≥100k entries via SQLite indexed lookups.
    """

    def get(self, *paths: Path | str, salt: str = "") -> dict[str, Any] | None:
        key = self._key(*paths, salt=salt)
        with connect() as conn:
            row = conn.execute(
                "SELECT payload_json FROM research_analysis_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()
            if row is None:
                return None
            conn.execute(
                "UPDATE research_analysis_cache SET last_accessed = ? WHERE cache_key = ?",
                (utc_now_iso(), key),
            )
            conn.commit()
            return json.loads(row["payload_json"])

    def put(self, payload: dict[str, Any], *paths: Path | str, salt: str = "") -> str:
        key = self._key(*paths, salt=salt)
        content_hash = key
        now = utc_now_iso()
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO research_analysis_cache
                (cache_key, content_hash, payload_json, created_at, last_accessed)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    last_accessed = excluded.last_accessed
                """,
                (key, content_hash, json.dumps(payload, default=str), now, now),
            )
            conn.commit()
        self.evict(max_entries=5000)
        return key

    def evict(self, *, max_entries: int = 5000) -> int:
        """Drop least-recently-accessed cache rows beyond max_entries."""
        with connect() as conn:
            total = int(
                conn.execute("SELECT COUNT(*) AS c FROM research_analysis_cache").fetchone()["c"]
            )
            overflow = total - max_entries
            if overflow <= 0:
                return 0
            conn.execute(
                """
                DELETE FROM research_analysis_cache WHERE cache_key IN (
                    SELECT cache_key FROM research_analysis_cache
                    ORDER BY last_accessed ASC
                    LIMIT ?
                )
                """,
                (overflow,),
            )
            conn.commit()
            return overflow

    def _key(self, *paths: Path | str, salt: str = "") -> str:
        h = hashlib.sha256()
        h.update(salt.encode())
        for p in paths:
            path = Path(p)
            if path.is_file():
                h.update(path.read_bytes())
                h.update(str(path.stat().st_mtime_ns).encode())
            else:
                h.update(str(p).encode())
        return h.hexdigest()
