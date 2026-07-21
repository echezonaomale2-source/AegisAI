"""Vision testing framework — folder batch runs + annotation accuracy reports."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from cv.models import VisionChartResult
from cv.vision_engine import VisionEngine


@dataclass
class CaseResult:
    image: str
    status: str
    expected: dict
    predicted: dict
    matches: dict[str, bool] = field(default_factory=dict)
    score: float = 0.0


@dataclass
class AccuracyReport:
    total: int
    passed: int
    failed: int
    accuracy: float
    field_accuracy: dict[str, float]
    cases: list[CaseResult]

    def as_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy": round(self.accuracy, 4),
            "field_accuracy": {k: round(v, 4) for k, v in self.field_accuracy.items()},
            "cases": [
                {
                    "image": c.image,
                    "status": c.status,
                    "expected": c.expected,
                    "predicted": c.predicted,
                    "matches": c.matches,
                    "score": round(c.score, 4),
                }
                for c in self.cases
            ],
        }


def _predict_fields(result: VisionChartResult) -> dict:
    summary = result.summary or {}
    return {
        "status": result.status,
        "pair": result.meta.pair,
        "timeframe": result.meta.timeframe,
        "trend": summary.get("trend", "Unknown"),
        "bos": bool(summary.get("bos")),
        "choch": bool(summary.get("choch")),
        "liquidity": summary.get("liquidity"),
        "liquidity_sweep": bool(summary.get("liquidity_sweep")),
        "bullish_order_block": bool(summary.get("bullish_order_block")),
        "bearish_order_block": bool(summary.get("bearish_order_block")),
        "bullish_fvg": summary.get("fvg_type") == "Bullish FVG" or bool(summary.get("bullish_fvg")),
        "bearish_fvg": summary.get("fvg_type") == "Bearish FVG" or bool(summary.get("bearish_fvg")),
        "supply": bool(summary.get("supply_zone") or summary.get("supply")),
        "demand": bool(summary.get("demand_zone") or summary.get("demand")),
        "candle_count_min": result.summary.get("candle_count", 0) if result.summary else len(result.candles),
    }


class VisionTestHarness:
    """
    Load a folder of screenshots + optional annotations JSON.

    Annotation file format (annotations.json):
    {
      "chart_a.png": {
        "pair": "EURUSD",
        "timeframe": "4H",
        "trend": "Bullish",
        "bos": true,
        "liquidity_sweep": true
      }
    }
    """

    def __init__(self, engine: VisionEngine | None = None) -> None:
        self.engine = engine or VisionEngine(use_cache=False)

    def run_folder(
        self,
        folder: str | Path,
        *,
        annotations_path: str | Path | None = None,
        output_dir: str | Path | None = None,
    ) -> AccuracyReport:
        root = Path(folder)
        images = sorted(
            {
                p.resolve()
                for pattern in ("*.png", "*.jpg", "*.jpeg", "*.PNG", "*.JPG", "*.JPEG")
                for p in root.glob(pattern)
            }
        )
        annotations: dict = {}
        ann_file = Path(annotations_path) if annotations_path else root / "annotations.json"
        if ann_file.exists():
            annotations = json.loads(ann_file.read_text(encoding="utf-8"))

        out = Path(output_dir) if output_dir else root / "vision_results"
        out.mkdir(parents=True, exist_ok=True)

        cases: list[CaseResult] = []
        field_hits: dict[str, list[bool]] = {}

        for image in images:
            result = self.engine.analyze_chart(image)
            predicted = _predict_fields(result)
            expected = annotations.get(image.name, {})
            (out / f"{image.stem}.features.json").write_text(
                result.model_dump_json(indent=2),
                encoding="utf-8",
            )

            matches: dict[str, bool] = {}
            if expected:
                for key, value in expected.items():
                    if key == "candle_count_min":
                        ok = int(predicted.get("candle_count_min", 0)) >= int(value)
                    else:
                        ok = predicted.get(key) == value
                    matches[key] = ok
                    field_hits.setdefault(key, []).append(ok)
                score = sum(1 for v in matches.values() if v) / max(len(matches), 1)
            else:
                score = 1.0 if result.status == "ok" else 0.0
                matches = {"status_ok": result.status == "ok"}
                field_hits.setdefault("status_ok", []).append(result.status == "ok")

            cases.append(
                CaseResult(
                    image=image.name,
                    status=result.status,
                    expected=expected,
                    predicted=predicted,
                    matches=matches,
                    score=score,
                )
            )

        passed = sum(1 for c in cases if c.score >= 0.999 or (c.expected and c.score >= 0.8))
        # Stricter: case passes if all annotated fields match, or no annotation and status ok.
        passed = 0
        for c in cases:
            if not c.expected:
                passed += 1 if c.status == "ok" else 0
            else:
                passed += 1 if all(c.matches.values()) else 0

        field_accuracy = {
            key: (sum(1 for x in vals if x) / len(vals) if vals else 0.0)
            for key, vals in field_hits.items()
        }
        total = len(cases)
        report = AccuracyReport(
            total=total,
            passed=passed,
            failed=total - passed,
            accuracy=(passed / total) if total else 0.0,
            field_accuracy=field_accuracy,
            cases=cases,
        )
        (out / "accuracy_report.json").write_text(
            json.dumps(report.as_dict(), indent=2),
            encoding="utf-8",
        )
        return report
