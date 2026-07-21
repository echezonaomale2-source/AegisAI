"""Engine 8 — Memory Engine: permanent storage of cognitive artifacts."""

from __future__ import annotations

import json
from pathlib import Path

from cognitive.events import EVT_MEMORY_STORED, EventBus
from cognitive.models.decision import CognitiveDecision
from core.logging_setup import get_logger
from memory.memory_service import MemoryService as LegacyMemory
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from storage.trade_store import TradeStore

log = get_logger("cognitive.memory")


class CognitiveMemoryEngine:
    """
    Remember everything — charts, evidence, reasoning, decision, outcomes.

    Nothing is deleted. History is never overwritten (append / upsert by trade_id).
    """

    def __init__(
        self,
        legacy: LegacyMemory | None = None,
        trade_store: TradeStore | None = None,
        bus: EventBus | None = None,
        archive_root: Path | None = None,
    ) -> None:
        self._legacy = legacy or LegacyMemory()
        self._store = trade_store or TradeStore()
        self._bus = bus
        self._archive = archive_root or (
            Path(__file__).resolve().parents[2] / "storage" / "cognitive_archive"
        )
        self._archive.mkdir(parents=True, exist_ok=True)

    def remember(
        self,
        decision: CognitiveDecision,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        legacy_decision: TradeDecision | None = None,
    ) -> TradeDecision:
        td = legacy_decision or self._to_legacy_stub(decision)
        td = self._store.save(
            td,
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
        )
        trade_dir = self._store.root / (td.trade_id or "")
        p4 = next(trade_dir.glob("chart_4h.*"))
        p1 = next(trade_dir.glob("chart_1h.*"))
        p15 = next(trade_dir.glob("chart_15m.*"))

        self._legacy.remember_decision(td, chart_4h=p4, chart_1h=p1, chart_15m=p15)

        # Permanent cognitive archive (never deleted) — encrypted at rest.
        archive_file = self._archive / f"{td.trade_id}.json"
        payload = json.dumps(
            {
                "trade_id": td.trade_id,
                "stored_at": utc_now_iso(),
                "cognitive_decision": decision.model_dump(mode="json"),
                "reasoning": decision.reasoning.model_dump(mode="json") if decision.reasoning else None,
                "risk": decision.risk.model_dump(mode="json") if decision.risk else None,
                "evidence": (
                    decision.reasoning.evidence_snapshot.model_dump(mode="json")
                    if decision.reasoning and decision.reasoning.evidence_snapshot
                    else None
                ),
                "reproducible_hash": decision.reproducible_hash,
            },
            indent=2,
            default=str,
        )
        from config.settings import settings
        from core.security.encryption import get_encryptor

        if settings.encrypt_memory_at_rest:
            payload = get_encryptor().encrypt_text(payload)
        archive_file.write_text(payload, encoding="utf-8")
        log.info("memory stored trade_id=%s archive=%s", td.trade_id, archive_file.name)
        if self._bus:
            self._bus.publish(EVT_MEMORY_STORED, {"trade_id": td.trade_id})
        return td

    def load_archive(self, trade_id: str) -> dict | None:
        """Load and decrypt a cognitive archive record."""
        path = self._archive / f"{trade_id}.json"
        if not path.exists():
            return None
        raw = path.read_text(encoding="utf-8")
        from core.security.encryption import get_encryptor

        raw = get_encryptor().decrypt_text(raw)
        return json.loads(raw)

    def apply_memory_bias(self, decision: TradeDecision) -> TradeDecision:
        return self._legacy.apply_memory_to_decision(decision)

    def _to_legacy_stub(self, decision: CognitiveDecision) -> TradeDecision:
        empty = ChartAnalysis(status="error", error="cognitive-only")
        scorecard = ConfidenceScorecard(
            htf_4h_alignment=0,
            mtf_1h_alignment=0,
            ltf_15m_confirmation=0,
            liquidity=0,
            order_block=0,
            fair_value_gap=0,
            market_structure=0,
            overall=decision.confidence,
            weights={},
        )
        return TradeDecision(
            pair=decision.pair,
            timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
            analysis_4h=empty,
            analysis_1h=empty,
            analysis_15m=empty,
            overall_bias=decision.recommendation,
            entry=decision.entry,
            stop_loss=decision.stop_loss,
            take_profit=decision.take_profit,
            risk_reward=decision.risk_reward,
            target_liquidity="Cognitive",
            confidence=decision.confidence,
            confidence_scorecard=scorecard,
            explanation=decision.explanation,
            reasons=list(decision.reasons),
            warnings=list(decision.warnings),
            generated_at=utc_now_iso(),
        )
