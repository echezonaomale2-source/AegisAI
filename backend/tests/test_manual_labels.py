"""Manual chart labels — no OCR."""

from vision.chart_parser import apply_manual_labels, normalize_pair, normalize_timeframe, parse_chart_labels


def test_normalize_pair() -> None:
    assert normalize_pair("eur/usd") == "EURUSD"
    assert normalize_pair("UNKNOWN") == "Unknown"
    assert normalize_pair("") == "Unknown"


def test_normalize_timeframe_aliases() -> None:
    assert normalize_timeframe("H4") == "4H"
    assert normalize_timeframe("m15") == "15M"
    assert normalize_timeframe(None, default="1H") == "1H"


def test_apply_manual_labels_ignores_image() -> None:
    labels = apply_manual_labels(pair="XAUUSD", expected_timeframe="4H")
    assert labels.pair == "XAUUSD"
    assert labels.timeframe == "4H"
    assert labels.pair_confidence == 100.0
    assert labels.timeframe_confidence == 100.0
    assert labels.raw_text == ""


def test_parse_chart_labels_compat_no_ocr() -> None:
    labels = parse_chart_labels(None, expected_timeframe="1H", pair="GBPUSD")
    assert labels.pair == "GBPUSD"
    assert labels.timeframe == "1H"
