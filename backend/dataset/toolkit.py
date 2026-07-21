"""
Annotated chart dataset tooling (Step 12).

Never invents labels. Import copies screenshots and writes empty annotation
stubs for human labeling. Validation rejects incomplete required keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ANNOTATION_FIELDS = (
    "trend",
    "bos",
    "choch",
    "liquidity",
    "liquidity_sweep",
    "bullish_order_block",
    "bearish_order_block",
    "bullish_fvg",
    "bearish_fvg",
    "supply",
    "demand",
    "pair",
    "timeframe",
)

# Human must fill these before an entry is considered labeled.
REQUIRED_FOR_LABELED = ("trend", "pair", "timeframe")

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}


def _utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def dataset_root(base: Path | None = None) -> Path:
    root = base or (Path(__file__).resolve().parents[1] / "cv_datasets")
    root.mkdir(parents=True, exist_ok=True)
    return root


def version_dir(version: str, base: Path | None = None) -> Path:
    path = dataset_root(base) / version
    path.mkdir(parents=True, exist_ok=True)
    (path / "images").mkdir(exist_ok=True)
    (path / "reports").mkdir(exist_ok=True)
    return path


def empty_annotation() -> dict[str, Any]:
    return {
        "trend": None,  # Bullish | Bearish | Range | Unknown — human only
        "bos": None,
        "choch": None,
        "liquidity": None,
        "liquidity_sweep": None,
        "bullish_order_block": None,
        "bearish_order_block": None,
        "bullish_fvg": None,
        "bearish_fvg": None,
        "supply": None,
        "demand": None,
        "pair": None,
        "timeframe": None,
        "notes": "",
        "labeled": False,
        "labeler": None,
        "labeled_at": None,
    }


def import_images(
    source: Path,
    *,
    version: str,
    base: Path | None = None,
) -> dict[str, Any]:
    """
    Copy screenshots into versioned dataset and create annotation stubs.
    Does NOT invent labels.
    """
    vdir = version_dir(version, base)
    ann_path = vdir / "annotations.json"
    annotations: dict[str, Any] = {}
    if ann_path.exists():
        annotations = json.loads(ann_path.read_text(encoding="utf-8"))

    source = Path(source)
    files = []
    if source.is_file():
        files = [source]
    else:
        files = [
            p
            for p in sorted(source.rglob("*"))
            if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
        ]

    imported = 0
    for src in files:
        dest_name = src.name
        dest = vdir / "images" / dest_name
        # Avoid overwrite collisions
        if dest.exists() and hashlib.sha1(dest.read_bytes()).hexdigest() != hashlib.sha1(
            src.read_bytes()
        ).hexdigest():
            dest_name = f"{src.stem}_{hashlib.sha1(src.read_bytes()).hexdigest()[:8]}{src.suffix}"
            dest = vdir / "images" / dest_name
        shutil.copy2(src, dest)
        if dest_name not in annotations:
            annotations[dest_name] = empty_annotation()
            imported += 1

    _write_manifest(vdir, annotations)
    ann_path.write_text(json.dumps(annotations, indent=2), encoding="utf-8")
    return {
        "version": version,
        "imported_new": imported,
        "total_entries": len(annotations),
        "path": str(vdir),
    }


def validate_dataset(version: str, *, base: Path | None = None) -> dict[str, Any]:
    vdir = version_dir(version, base)
    ann_path = vdir / "annotations.json"
    if not ann_path.exists():
        return {"ok": False, "errors": ["annotations.json missing"], "labeled": 0, "unlabeled": 0}

    annotations = json.loads(ann_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    labeled = unlabeled = 0
    for name, ann in annotations.items():
        img = vdir / "images" / name
        if not img.exists():
            errors.append(f"missing image: {name}")
            continue
        if _is_labeled(ann):
            labeled += 1
            for key in REQUIRED_FOR_LABELED:
                if ann.get(key) in (None, "", "Unknown"):
                    errors.append(f"{name}: required field '{key}' empty")
        else:
            unlabeled += 1
            # Ensure no fake auto-labels slipped in
            if ann.get("labeled") is True and any(
                ann.get(k) is None for k in REQUIRED_FOR_LABELED
            ):
                errors.append(f"{name}: marked labeled but required fields missing")

    return {
        "ok": len(errors) == 0,
        "errors": errors[:50],
        "labeled": labeled,
        "unlabeled": unlabeled,
        "total": len(annotations),
        "version": version,
    }


def compare_to_ai(
    version: str,
    *,
    base: Path | None = None,
    persist_eval: bool = True,
) -> dict[str, Any]:
    """Run Vision harness against labeled annotations only. Never invents expected labels."""
    from cv.testing.harness import VisionTestHarness
    from evaluation.engine import EvaluationEngine

    vdir = version_dir(version, base)
    ann_path = vdir / "annotations.json"
    annotations = json.loads(ann_path.read_text(encoding="utf-8")) if ann_path.exists() else {}
    labeled = {
        k: _ann_to_expected(v)
        for k, v in annotations.items()
        if _is_labeled(v)
    }
    # Write filtered annotations for harness
    filtered_path = vdir / "annotations.labeled.json"
    filtered_path.write_text(json.dumps(labeled, indent=2), encoding="utf-8")

    report = VisionTestHarness().run_folder(
        vdir / "images",
        annotations_path=filtered_path,
        output_dir=vdir / "reports" / "latest",
    )
    payload = report.as_dict()
    payload["dataset_version"] = version
    payload["labeled_only"] = True
    payload["compared_at"] = _utc()
    out = vdir / "reports" / f"compare_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.json"
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    mismatches = sum(1 for c in report.cases if c.expected and not all(c.matches.values()))
    matches = sum(1 for c in report.cases if c.expected and all(c.matches.values()))
    if persist_eval:
        EvaluationEngine().record_annotation_compare(matches=matches, mismatches=mismatches)

    return payload


def _is_labeled(ann: dict[str, Any]) -> bool:
    if ann.get("labeled") is True:
        return True
    return all(ann.get(k) not in (None, "") for k in REQUIRED_FOR_LABELED)


def _ann_to_expected(ann: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ANNOTATION_FIELDS:
        val = ann.get(key)
        if val is None:
            continue
        out[key] = val
    return out


def _write_manifest(vdir: Path, annotations: dict[str, Any]) -> None:
    images = sorted((vdir / "images").glob("*"))
    checksums = {
        p.name: hashlib.sha1(p.read_bytes()).hexdigest()
        for p in images
        if p.is_file()
    }
    manifest = {
        "dataset_version": vdir.name,
        "created_or_updated": _utc(),
        "entry_count": len(annotations),
        "image_checksums": checksums,
        "schema": "aegis.cv_dataset.v1",
        "rule": "Never invent labels — human annotation required.",
    }
    (vdir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AegisAI annotated dataset tools")
    sub = parser.add_subparsers(dest="cmd", required=True)

    imp = sub.add_parser("import", help="Import screenshots (empty annotation stubs)")
    imp.add_argument("source", type=Path)
    imp.add_argument("--version", required=True)

    val = sub.add_parser("validate", help="Validate dataset annotations")
    val.add_argument("--version", required=True)

    cmp_ = sub.add_parser("compare", help="Compare AI detections vs human labels")
    cmp_.add_argument("--version", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "import":
        print(json.dumps(import_images(args.source, version=args.version), indent=2))
    elif args.cmd == "validate":
        print(json.dumps(validate_dataset(args.version), indent=2))
    elif args.cmd == "compare":
        print(json.dumps(compare_to_ai(args.version), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
