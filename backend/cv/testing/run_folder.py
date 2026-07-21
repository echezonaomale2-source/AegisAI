"""CLI: python -m cv.testing.run_folder <folder> [--annotations path] [--out path]"""

from __future__ import annotations

import argparse
import json

from cv.testing.harness import VisionTestHarness


def main() -> None:
    parser = argparse.ArgumentParser(description="AegisAI Phase 5 vision test harness")
    parser.add_argument("folder", help="Folder of chart screenshots")
    parser.add_argument("--annotations", default=None, help="Optional annotations.json path")
    parser.add_argument("--out", default=None, help="Output directory for features + report")
    args = parser.parse_args()

    report = VisionTestHarness().run_folder(
        args.folder,
        annotations_path=args.annotations,
        output_dir=args.out,
    )
    print(json.dumps(report.as_dict(), indent=2))


if __name__ == "__main__":
    main()
