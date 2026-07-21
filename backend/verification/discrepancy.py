"""
Discrepancy reporter — formats and persists verification discrepancies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from verification.models import Discrepancy, VerificationSummary


class DiscrepancyReporter:
    """
    Store discrepancies for later review and emit human-readable warnings.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (
            Path(__file__).resolve().parent.parent / "storage" / "verification_discrepancies"
        )
        self.root.mkdir(parents=True, exist_ok=True)

    def warnings_for(self, summary: VerificationSummary) -> list[str]:
        """Build final-report warning strings from a verification summary."""
        warnings: list[str] = list(summary.warnings)
        if summary.screenshot_only or summary.status == "screenshot_only":
            warnings.append(
                "Recommendation based on screenshots only — market data verification was not applied."
            )
            return list(dict.fromkeys(warnings))

        if summary.status == "unavailable":
            warnings.append(
                "Market data unavailable — continuing with screenshot analysis only."
            )
        elif summary.status == "error":
            warnings.append(
                "Market data verification failed — continuing with screenshot analysis only."
            )

        for d in summary.discrepancies:
            label = d.kind.replace("_", " ")
            line = f"Market verification: {label} — {d.message}"
            if d.screenshot_value and d.market_value:
                line += f" (screenshot={d.screenshot_value}, market={d.market_value})"
            warnings.append(line)

        if summary.significant_disagreement:
            warnings.append(
                "Significant disagreement between screenshot reconstruction and market data — "
                "confidence reduced."
            )

        return list(dict.fromkeys(warnings))

    def save(
        self,
        summary: VerificationSummary,
        *,
        trade_id: str | None = None,
    ) -> Path | None:
        """Persist discrepancies when any exist (or on conflict status)."""
        if not summary.discrepancies and summary.status not in {
            "verified_conflict",
            "error",
            "unavailable",
        }:
            # Still record screenshot_only lightly? Skip noise — only store meaningful events.
            if summary.status == "screenshot_only":
                return None

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        name = f"{trade_id or 'anon'}_{stamp}.json"
        path = self.root / name
        payload = {
            "saved_at": datetime.now(timezone.utc).isoformat(),
            "trade_id": trade_id,
            "summary": summary.model_dump(mode="json"),
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def list_recent(self, limit: int = 50) -> list[dict]:
        files = sorted(self.root.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        out: list[dict] = []
        for path in files[:limit]:
            try:
                out.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                continue
        return out

    @staticmethod
    def format_discrepancy(d: Discrepancy) -> str:
        return f"[{d.severity}] {d.kind}: {d.message}"
