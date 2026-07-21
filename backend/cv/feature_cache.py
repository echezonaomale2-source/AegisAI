"""Feature Cache — skip reprocessing unchanged screenshots (with eviction)."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from config.settings import settings
from cv.models import VisionChartResult

DEFAULT_MAX_FILES = 400


class FeatureCache:
    def __init__(
        self,
        root: Path | None = None,
        *,
        max_files: int = DEFAULT_MAX_FILES,
    ) -> None:
        self.root = root or (settings.upload_dir.parent / "storage" / "vision_cache")
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_files = max_files

    def _key_for(
        self,
        image_path: str,
        expected_timeframe: str | None,
        *,
        pair: str | None = None,
    ) -> str:
        path = Path(image_path)
        digest = hashlib.sha1()
        digest.update(path.name.encode("utf-8"))
        digest.update(str(path.stat().st_mtime_ns).encode("utf-8"))
        digest.update(str(path.stat().st_size).encode("utf-8"))
        digest.update((expected_timeframe or "").encode("utf-8"))
        digest.update((pair or "").encode("utf-8"))
        # Content hash for correctness when timestamps collide.
        with path.open("rb") as handle:
            digest.update(handle.read())
        return digest.hexdigest()

    def get(
        self,
        image_path: str,
        expected_timeframe: str | None = None,
        *,
        pair: str | None = None,
    ) -> VisionChartResult | None:
        key = self._key_for(image_path, expected_timeframe, pair=pair)
        cache_path = self.root / f"{key}.json"
        if not cache_path.exists():
            return None
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
            result = VisionChartResult.model_validate(data)
            result.cache_hit = True
            # Touch mtime for LRU eviction
            cache_path.touch(exist_ok=True)
            return result
        except Exception:
            return None

    def put(
        self,
        image_path: str,
        result: VisionChartResult,
        expected_timeframe: str | None = None,
        *,
        pair: str | None = None,
    ) -> None:
        key = self._key_for(image_path, expected_timeframe, pair=pair)
        cache_path = self.root / f"{key}.json"
        payload = result.model_dump()
        payload["cache_hit"] = False
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
        self.evict_if_needed()

    def evict_if_needed(self) -> int:
        """Remove oldest cache files when over max_files. Returns count removed."""
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime)
        overflow = len(files) - self.max_files
        if overflow <= 0:
            return 0
        removed = 0
        for path in files[:overflow]:
            try:
                path.unlink(missing_ok=True)
                removed += 1
            except OSError:
                pass
        return removed
