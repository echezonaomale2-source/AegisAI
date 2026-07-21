"""Persistent local storage for completed trade decisions (optionally encrypted)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from config.settings import settings
from core.analysis_jobs import ANALYSIS_SCHEMA_VERSION
from core.logging_setup import get_logger
from core.security.encryption import get_encryptor
from models.decision_schemas import TradeDecision

log = get_logger("storage.trades")


class TradeStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or settings.trades_dir
        self.root.mkdir(parents=True, exist_ok=True)
        self.quarantine = self.root.parent / "trades_quarantine"
        self.quarantine.mkdir(parents=True, exist_ok=True)
        self._encrypt = bool(settings.encrypt_trade_records)
        self._encrypt_charts = bool(settings.encrypt_charts)

    def _copy_chart(self, source: Path, destination: Path) -> None:
        data = Path(source).read_bytes()
        if self._encrypt_charts:
            data = get_encryptor().encrypt_file_bytes(data)
        destination.write_bytes(data)

    def read_chart_bytes(self, path: Path | str) -> bytes:
        data = Path(path).read_bytes()
        return get_encryptor().decrypt_file_bytes(data)

    def _write_decision(self, path: Path, payload: dict) -> None:
        text = json.dumps(payload, indent=2)
        if self._encrypt:
            text = get_encryptor().encrypt_text(text)
            path.write_text(text, encoding="utf-8")
        else:
            path.write_text(text, encoding="utf-8")

    def _read_decision(self, path: Path) -> dict:
        raw = path.read_text(encoding="utf-8")
        if raw.startswith("enc:v1:"):
            raw = get_encryptor().decrypt_text(raw)
        data = json.loads(raw)
        # Backward compatible — default schema version if older records lack it.
        data.setdefault("analysis_schema_version", "0.9")
        return data

    def save(
        self,
        decision: TradeDecision,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
    ) -> TradeDecision:
        trade_id = uuid.uuid4().hex
        trade_dir = self.root / trade_id
        trade_dir.mkdir(parents=True, exist_ok=True)

        saved_paths = {}
        for label, source in (
            ("4h", chart_4h),
            ("1h", chart_1h),
            ("15m", chart_15m),
        ):
            suffix = Path(source).suffix.lower() or ".jpg"
            destination = trade_dir / f"chart_{label}{suffix}"
            self._copy_chart(source, destination)
            saved_paths[label] = str(destination)

        decision.trade_id = trade_id
        payload = {
            "id": trade_id,
            "timestamp": decision.generated_at,
            "pair": decision.pair,
            "timeframes": decision.timeframes,
            "overall_bias": decision.overall_bias,
            "entry": decision.entry,
            "stop_loss": decision.stop_loss,
            "take_profit": decision.take_profit,
            "risk_reward": decision.risk_reward,
            "target_liquidity": decision.target_liquidity,
            "confidence": decision.confidence,
            "confidence_scorecard": decision.confidence_scorecard.model_dump(),
            "explanation": decision.explanation,
            "reasons": decision.reasons,
            "warnings": decision.warnings,
            "status": decision.status,
            "outcome": None,
            "outcome_chart": None,
            "lesson": None,
            "screenshots": saved_paths,
            "extracted_features": {
                "4h": decision.analysis_4h.model_dump(),
                "1h": decision.analysis_1h.model_dump(),
                "15m": decision.analysis_15m.model_dump(),
            },
            "final_decision": decision.overall_bias,
            "encrypted": self._encrypt,
            "charts_encrypted": self._encrypt_charts,
            "analysis_schema_version": ANALYSIS_SCHEMA_VERSION,
        }

        self._write_decision(trade_dir / "decision.json", payload)
        log.info("saved trade %s encrypted=%s", trade_id, self._encrypt)
        return decision

    def update_outcome(
        self,
        trade_id: str,
        *,
        outcome: str,
        outcome_chart: Path,
        lesson: str,
    ) -> dict:
        trade_dir = self.root / trade_id
        decision_path = trade_dir / "decision.json"
        if not decision_path.exists():
            raise FileNotFoundError(f"Trade {trade_id} not found")

        payload = self._read_decision(decision_path)

        dest = trade_dir / f"outcome{outcome_chart.suffix.lower() or '.jpg'}"
        self._copy_chart(outcome_chart, dest)
        payload["outcome"] = outcome
        payload["outcome_chart"] = str(dest)
        payload["lesson"] = lesson
        payload["charts_encrypted"] = self._encrypt_charts
        payload["status"] = (
            "TP"
            if outcome == "TAKE_PROFIT"
            else "BE"
            if outcome == "BREAK_EVEN"
            else "SL"
        )

        self._write_decision(decision_path, payload)
        return payload

    def list_trades(self) -> list[dict]:
        records: list[dict] = []
        for path in sorted(self.root.glob("*/decision.json"), reverse=True):
            try:
                records.append(self._read_decision(path))
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                log.warning("quarantine corrupted trade record %s: %s", path, exc)
                self._quarantine(path.parent)
        return records

    def get_trade(self, trade_id: str) -> dict | None:
        path = self.root / trade_id / "decision.json"
        if not path.exists():
            return None
        try:
            return self._read_decision(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            log.error("failed to read trade %s: %s — quarantining", trade_id, exc)
            self._quarantine(path.parent)
            return None

    def _quarantine(self, trade_dir: Path) -> None:
        try:
            dest = self.quarantine / trade_dir.name
            if dest.exists():
                dest = self.quarantine / f"{trade_dir.name}_{uuid.uuid4().hex[:6]}"
            trade_dir.rename(dest)
        except OSError as exc:
            log.error("quarantine failed for %s: %s", trade_dir, exc)
