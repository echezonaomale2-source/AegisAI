"""Step 7 — Memory Engine encryption tests."""

from __future__ import annotations

import json
from pathlib import Path

from cognitive.engines.memory_engine import CognitiveMemoryEngine
from cognitive.models.decision import CognitiveDecision
from config import settings as settings_mod
from core.security.encryption import FILE_PREFIX, PREFIX, get_encryptor, reset_encryptor
from memory.memory_repository import MemoryRepository
from memory.secure_fields import seal_text, unseal_text
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from storage.trade_store import TradeStore


def _tiny_png(path: Path) -> Path:
    # Minimal valid-ish PNG header bytes for copy/encrypt tests
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
        b"\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
    )
    return path


def test_seal_text_roundtrip(monkeypatch) -> None:
    monkeypatch.setattr(settings_mod.settings, "encrypt_memory_at_rest", True)
    reset_encryptor()
    sealed = seal_text("secret lesson")
    assert sealed is not None
    assert sealed.startswith(PREFIX)
    assert unseal_text(sealed) == "secret lesson"


def test_memory_repo_encrypts_sensitive_columns(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings_mod.settings, "encrypt_memory_at_rest", True)
    reset_encryptor()
    # Point DB to temp via monkeypatch of connect if needed — use real DB carefully.
    # Use repository with a unique trade_id and verify raw SQL is encrypted.
    from memory.database import connect

    trade_id = "memenc_" + "a" * 24
    repo = MemoryRepository()
    repo.upsert_memory(
        {
            "trade_id": trade_id,
            "timestamp": utc_now_iso(),
            "pair": "EURUSD",
            "timeframes": {"1H": "1H"},
            "features": {"bos": True},
            "analysis_4h": {"status": "ok"},
            "analysis_1h": {"status": "ok"},
            "analysis_15m": {"status": "ok"},
            "final_decision": "NO TRADE",
            "explanation": "private analysis text",
            "fingerprint_bits": "1010",
            "fingerprint_hash": "abc",
            "direction": "NO TRADE",
        }
    )
    with connect() as conn:
        raw = conn.execute(
            "SELECT explanation, features_json, fingerprint_bits FROM memories WHERE trade_id=?",
            (trade_id,),
        ).fetchone()
    assert raw["explanation"].startswith(PREFIX)
    assert raw["features_json"].startswith(PREFIX)
    assert raw["fingerprint_bits"] == "1010"  # similarity stays plaintext
    got = repo.get(trade_id)
    assert got is not None
    assert got["explanation"] == "private analysis text"
    assert json.loads(got["features_json"])["bos"] is True
    with connect() as conn:
        conn.execute("DELETE FROM memories WHERE trade_id=?", (trade_id,))
        conn.commit()


def test_trade_store_encrypts_charts(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings_mod.settings, "encrypt_charts", True)
    monkeypatch.setattr(settings_mod.settings, "encrypt_trade_records", True)
    reset_encryptor()
    img = _tiny_png(tmp_path / "c.png")
    chart = ChartAnalysis(status="ok", pair="EURUSD", timeframe="1H", confidence=50)
    td = TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart,
        analysis_1h=chart,
        analysis_15m=chart,
        overall_bias="NO TRADE",
        entry="—",
        stop_loss="—",
        take_profit="—",
        risk_reward="—",
        target_liquidity="—",
        confidence=40,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=40,
            mtf_1h_alignment=40,
            ltf_15m_confirmation=40,
            liquidity=40,
            order_block=40,
            fair_value_gap=40,
            market_structure=40,
            overall=40,
            weights={},
        ),
        explanation="test",
        generated_at=utc_now_iso(),
    )
    store = TradeStore(root=tmp_path / "trades")
    saved = store.save(td, chart_4h=img, chart_1h=img, chart_15m=img)
    trade_dir = tmp_path / "trades" / (saved.trade_id or "")
    chart_path = next(trade_dir.glob("chart_4h.*"))
    on_disk = chart_path.read_bytes()
    assert on_disk.startswith(FILE_PREFIX)
    assert store.read_chart_bytes(chart_path).startswith(b"\x89PNG")


def test_cognitive_archive_encrypted(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings_mod.settings, "encrypt_memory_at_rest", True)
    monkeypatch.setattr(settings_mod.settings, "encrypt_charts", True)
    monkeypatch.setattr(settings_mod.settings, "encrypt_trade_records", True)
    reset_encryptor()
    img = _tiny_png(tmp_path / "c.png")
    decision = CognitiveDecision(
        pair="EURUSD",
        recommendation="NO TRADE",
        confidence=40,
        trade_grade="F",
        explanation="archive me",
    )
    eng = CognitiveMemoryEngine(
        archive_root=tmp_path / "archive",
        trade_store=TradeStore(root=tmp_path / "trades"),
    )
    td = eng.remember(decision, chart_4h=img, chart_1h=img, chart_15m=img)
    raw = (tmp_path / "archive" / f"{td.trade_id}.json").read_text(encoding="utf-8")
    assert raw.startswith(PREFIX)
    loaded = eng.load_archive(td.trade_id or "")
    assert loaded is not None
    assert loaded["cognitive_decision"]["explanation"] == "archive me"
