"""
Engine 9 — Learning Engine (cognitive facade).

Incremental feature-weight nudges only. Never retrains from a single trade.
Full outcome pipeline SSOT is ResearchOrchestrator.process_outcome.
Historical memory rows are never rewritten beyond outcome fields.
"""

from __future__ import annotations

import json
from pathlib import Path

from cognitive.events import EVT_LEARNING_UPDATED, EventBus
from cognitive.weights import DEFAULT_FEATURE_WEIGHTS
from core.logging_setup import get_logger
from memory.outcome_utils import is_neutral, is_win, normalize_outcome

log = get_logger("cognitive.learning")

# Cap per-trade reliability move — single trades must not dominate.
MAX_RELIABILITY_DELTA = 0.02
MIN_STRENGTH_TO_NUDGE = 0.35


class CognitiveLearningEngine:
    def __init__(
        self,
        bus: EventBus | None = None,
        weights_path: Path | None = None,
    ) -> None:
        self._bus = bus
        self._weights_path = weights_path or (
            Path(__file__).resolve().parents[2] / "storage" / "cognitive_feature_weights.json"
        )
        self._weights = self._load_weights()
        self._nudge_events = 0

    def current_weights(self) -> dict[str, float]:
        return dict(self._weights)

    def learn_from_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart_path: str | None = None,
        feature_types: list[str] | None = None,
        grade: str | None = None,
        learning_strength: float = 1.0,
        skip_full_pipeline: bool = True,
    ) -> dict:
        """
        Apply an incremental cognitive weight nudge for the trade's features.

        By default does NOT re-run MemoryService (avoids double-counting when
        ResearchOrchestrator already processed the outcome). Pass
        skip_full_pipeline=False only for isolated unit tests that need the
        legacy memory path.
        """
        _ = outcome_chart_path
        result: dict = {"trade_id": trade_id, "outcome": normalize_outcome(outcome)}

        if not skip_full_pipeline:
            from memory.memory_service import MemoryService

            result.update(
                MemoryService().learn_from_outcome(
                    trade_id,
                    outcome=outcome,
                    outcome_chart_path=outcome_chart_path,
                )
            )
            grade = grade or result.get("grade")
            learning_strength = float(
                result.get("learning_applied") and result.get("learning_strength", 1.0) or 0.1
            )

        updates = self.apply_incremental_update(
            outcome=outcome,
            feature_types=feature_types or [],
            grade=grade or result.get("grade") or "C",
            learning_strength=learning_strength,
        )
        result["cognitive_weight_updates"] = updates
        result["nudge_events"] = self._nudge_events
        return result

    def apply_incremental_update(
        self,
        *,
        outcome: str,
        feature_types: list[str],
        grade: str = "C",
        learning_strength: float = 1.0,
    ) -> dict[str, float]:
        """
        Nudge reliability for listed features only.
        BREAK_EVEN → no weight change. Weak strength → no change.
        """
        outcome = normalize_outcome(outcome)
        if is_neutral(outcome):
            log.info("learning skip weight nudge for BREAK_EVEN")
            return {}
        if not feature_types:
            log.info("learning skip weight nudge — no feature_types (refuse broad retrain)")
            return {}
        strength = max(0.0, min(1.0, float(learning_strength)))
        if strength < MIN_STRENGTH_TO_NUDGE:
            log.info("learning skip weight nudge — strength %.2f below floor", strength)
            return {}

        delta = MAX_RELIABILITY_DELTA if is_win(outcome) else -MAX_RELIABILITY_DELTA * 0.75
        delta *= strength
        if grade in {"F", "D"}:
            delta *= 0.25
        elif grade in {"A+", "A"}:
            delta *= 1.1

        updates: dict[str, float] = {}
        for ftype in feature_types:
            if ftype not in DEFAULT_FEATURE_WEIGHTS and not ftype.startswith("_"):
                # Still allow known cognitive keys; skip unknowns rather than invent
                if ftype not in self._weights and ftype not in DEFAULT_FEATURE_WEIGHTS:
                    continue
            rel_key = f"_rel_{ftype}"
            reliability = float(self._weights.get(rel_key, 1.0))
            reliability = max(0.5, min(1.5, reliability + delta))
            self._weights[rel_key] = round(reliability, 4)
            default = DEFAULT_FEATURE_WEIGHTS.get(ftype, self._weights.get(ftype, 5.0))
            self._weights[ftype] = round(float(default) * reliability, 3)
            updates[ftype] = self._weights[ftype]

        if updates:
            self._nudge_events += 1
            self._save_weights()
            log.info(
                "learning incremental nudge outcome=%s features=%d delta=%.4f",
                outcome,
                len(updates),
                delta,
            )
            if self._bus:
                self._bus.publish(
                    EVT_LEARNING_UPDATED,
                    {"outcome": outcome, "updates": updates, "delta": delta},
                )
        return updates

    def historical_summary(self) -> dict:
        """Snapshot of cognitive weight state for dashboards."""
        rel = {k: v for k, v in self._weights.items() if k.startswith("_rel_")}
        return {
            "feature_weights": {
                k: v for k, v in self._weights.items() if not k.startswith("_")
            },
            "reliability": rel,
            "nudge_events": self._nudge_events,
            "weights_path": str(self._weights_path),
        }

    def _load_weights(self) -> dict[str, float]:
        if self._weights_path.exists():
            try:
                data = json.loads(self._weights_path.read_text(encoding="utf-8"))
                merged = dict(DEFAULT_FEATURE_WEIGHTS)
                merged.update({k: float(v) for k, v in data.items()})
                return merged
            except Exception as exc:  # noqa: BLE001
                log.warning("weight load failed: %s", exc)
        return dict(DEFAULT_FEATURE_WEIGHTS)

    def _save_weights(self) -> None:
        self._weights_path.parent.mkdir(parents=True, exist_ok=True)
        self._weights_path.write_text(
            json.dumps(self._weights, indent=2, sort_keys=True),
            encoding="utf-8",
        )
