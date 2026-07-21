"""Intermediate result cache — avoid repeating expensive image processing."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from config.settings import settings
from core.logging_setup import get_logger

log = get_logger("cache")

T = TypeVar("T", bound=BaseModel)


class IntermediateCache:
    """
    File-backed cache for ChartModel / FeatureSet / SMCAnalysis stages.

    Keyed by content hash of the source image + stage name + optional salt.
    Supports future GPU/model swaps by including a model_version salt.
    """

    def __init__(
        self,
        root: Path | None = None,
        *,
        model_version: str = "v1",
        enabled: bool = True,
    ) -> None:
        self.root = root or (settings.upload_dir.parent / "storage" / "core_cache")
        self.root.mkdir(parents=True, exist_ok=True)
        self.model_version = model_version
        self.enabled = enabled

    def _key(self, image_path: str | Path, stage: str, salt: str = "") -> str:
        path = Path(image_path)
        h = hashlib.sha256()
        h.update(self.model_version.encode())
        h.update(stage.encode())
        h.update(salt.encode())
        if path.is_file():
            h.update(path.read_bytes())
            h.update(str(path.stat().st_mtime_ns).encode())
        else:
            h.update(str(image_path).encode())
        return h.hexdigest()

    def get(self, image_path: str | Path, stage: str, model: type[T], *, salt: str = "") -> T | None:
        if not self.enabled:
            return None
        key = self._key(image_path, stage, salt)
        file = self.root / stage / f"{key}.json"
        if not file.exists():
            return None
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            log.debug("cache hit stage=%s key=%s", stage, key[:12])
            return model.model_validate(data)
        except Exception as exc:  # noqa: BLE001
            log.warning("cache read failed stage=%s: %s", stage, exc)
            return None

    def put(self, image_path: str | Path, stage: str, payload: BaseModel, *, salt: str = "") -> None:
        if not self.enabled:
            return
        key = self._key(image_path, stage, salt)
        folder = self.root / stage
        folder.mkdir(parents=True, exist_ok=True)
        file = folder / f"{key}.json"
        meta = {
            "_cached_at": time.time(),
            "_stage": stage,
            "_model_version": self.model_version,
            **payload.model_dump(),
        }
        # Strip meta keys that aren't part of the model by writing model dump only.
        file.write_text(payload.model_dump_json(indent=2), encoding="utf-8")
        # Keep a small sidecar for debugging.
        (folder / f"{key}.meta.json").write_text(json.dumps(meta, default=str)[:2000], encoding="utf-8")
        log.debug("cache put stage=%s key=%s", stage, key[:12])
        self.evict_stage(stage, max_files=300)

    def evict_stage(self, stage: str, *, max_files: int = 300) -> int:
        folder = self.root / stage
        if not folder.exists():
            return 0
        files = sorted(
            [p for p in folder.glob("*.json") if not p.name.endswith(".meta.json")],
            key=lambda p: p.stat().st_mtime,
        )
        overflow = len(files) - max_files
        if overflow <= 0:
            return 0
        removed = 0
        for path in files[:overflow]:
            path.unlink(missing_ok=True)
            meta = folder / f"{path.stem}.meta.json"
            meta.unlink(missing_ok=True)
            removed += 1
        return removed

    def clear_stage(self, stage: str) -> int:
        folder = self.root / stage
        if not folder.exists():
            return 0
        count = 0
        for f in folder.glob("*"):
            f.unlink(missing_ok=True)
            count += 1
        return count
