"""Step 1 infrastructure — encryption, settings, DI smoke tests."""

from __future__ import annotations

import json
from pathlib import Path

from cryptography.fernet import Fernet

from config.settings import Settings
from core.app_deps import get_analysis_service, get_app_services, reset_app_services
from core.security.encryption import LocalEncryptor, PREFIX, reset_encryptor
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from storage.trade_store import TradeStore


def _decision() -> TradeDecision:
    chart = ChartAnalysis(
        status="ok",
        pair="EURUSD",
        timeframe="4H",
        trend="Bullish",
        market_structure="Higher Highs",
        bos=True,
        confidence=80,
    )
    return TradeDecision(
        pair="EURUSD",
        timeframes={"4H": "4H", "1H": "1H", "15M": "15M"},
        analysis_4h=chart,
        analysis_1h=chart.model_copy(update={"timeframe": "1H"}),
        analysis_15m=chart.model_copy(update={"timeframe": "15M"}),
        overall_bias="BUY",
        entry="1.10",
        stop_loss="1.09",
        take_profit="1.13",
        risk_reward="3.00",
        target_liquidity="Equal highs",
        confidence=80,
        confidence_scorecard=ConfidenceScorecard(
            htf_4h_alignment=80,
            mtf_1h_alignment=75,
            ltf_15m_confirmation=70,
            liquidity=70,
            order_block=70,
            fair_value_gap=70,
            market_structure=80,
            overall=80,
            weights={},
        ),
        explanation="infra test",
        reasons=["bos"],
        warnings=[],
        generated_at=utc_now_iso(),
    )


def test_encryptor_roundtrip(tmp_path: Path, monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("AEGIS_ENCRYPTION_KEY", key.decode())
    reset_encryptor()
    enc = LocalEncryptor(key=key)
    cipher = enc.encrypt_text('{"ok": true}')
    assert cipher.startswith(PREFIX)
    assert enc.decrypt_text(cipher) == '{"ok": true}'
    assert enc.decrypt_text('{"plain":1}') == '{"plain":1}'


def test_trade_store_encrypted_roundtrip(tmp_path: Path, monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setenv("AEGIS_ENCRYPTION_KEY", key.decode())
    monkeypatch.setenv("AEGIS_ENCRYPT_TRADE_RECORDS", "true")
    reset_encryptor()

    # Point settings via TradeStore root override; encrypt flag from settings
    from config import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "encrypt_trade_records", True)
    monkeypatch.setattr(settings_mod.settings, "encryption_key", key.decode())
    reset_encryptor()

    store = TradeStore(root=tmp_path / "trades")
    store._encrypt = True

    # Create dummy chart files
    c4 = tmp_path / "4h.jpg"
    c1 = tmp_path / "1h.jpg"
    c15 = tmp_path / "15m.jpg"
    for p in (c4, c1, c15):
        p.write_bytes(b"fake")

    saved = store.save(_decision(), chart_4h=c4, chart_1h=c1, chart_15m=c15)
    assert saved.trade_id
    raw = (tmp_path / "trades" / saved.trade_id / "decision.json").read_text(encoding="utf-8")
    assert raw.startswith(PREFIX)
    loaded = store.get_trade(saved.trade_id)
    assert loaded is not None
    assert loaded["pair"] == "EURUSD"
    assert loaded["overall_bias"] == "BUY"


def test_settings_storage_paths():
    s = Settings()
    assert s.storage_root.name == "storage"
    assert s.trades_dir.name == "trades"
    assert s.cors_origin_list


def test_app_deps_singleton():
    reset_app_services()
    a = get_app_services()
    b = get_app_services()
    assert a is b
    assert get_analysis_service().brain is a.brain
