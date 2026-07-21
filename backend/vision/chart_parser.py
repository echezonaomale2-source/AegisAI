"""Apply user-selected pair and timeframe labels (no OCR)."""

from __future__ import annotations

from dataclasses import dataclass

KNOWN_TIMEFRAMES = frozenset(
    {"1M", "5M", "15M", "30M", "1H", "4H", "1D", "1W", "M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"}
)

# Normalize alternate notations to canonical labels used in the app.
_TF_ALIASES = {
    "M1": "1M",
    "M5": "5M",
    "M15": "15M",
    "M30": "30M",
    "H1": "1H",
    "H4": "4H",
    "D1": "1D",
    "W1": "1W",
}


@dataclass
class ChartLabels:
    pair: str
    timeframe: str
    detected_timeframe_label: str | None
    session_labels: list[str]
    pair_confidence: float
    timeframe_confidence: float
    raw_text: str


def normalize_pair(pair: str | None) -> str:
    clean = (pair or "").strip().upper().replace("/", "").replace(" ", "").replace("-", "")
    if not clean or clean in {"UNKNOWN", "UNK"}:
        return "Unknown"
    return clean


def normalize_timeframe(timeframe: str | None, *, default: str | None = None) -> str:
    raw = (timeframe or "").strip().upper().replace(" ", "")
    if not raw:
        return default or "Unknown"
    canonical = _TF_ALIASES.get(raw, raw)
    if canonical in KNOWN_TIMEFRAMES or canonical in _TF_ALIASES.values():
        return canonical
    # Allow custom labels the user typed; never invent from the image.
    return canonical if canonical else (default or "Unknown")


def apply_manual_labels(
    *,
    pair: str | None = None,
    expected_timeframe: str | None = None,
) -> ChartLabels:
    """
    Bind chart metadata from the user's selection only.

    Absolute prices are never invented from the image; pair/TF are never read
    from screenshot chrome.
    """
    resolved_pair = normalize_pair(pair)
    resolved_tf = normalize_timeframe(expected_timeframe)
    pair_conf = 100.0 if resolved_pair != "Unknown" else 0.0
    tf_conf = 100.0 if resolved_tf != "Unknown" else 0.0
    return ChartLabels(
        pair=resolved_pair,
        timeframe=resolved_tf,
        detected_timeframe_label=resolved_tf if resolved_tf != "Unknown" else None,
        session_labels=[],
        pair_confidence=pair_conf,
        timeframe_confidence=tf_conf,
        raw_text="",
    )


def parse_chart_labels(
    _full_bgr=None,
    expected_timeframe: str | None = None,
    *,
    pair: str | None = None,
) -> ChartLabels:
    """Compatibility wrapper — ignores image pixels; uses manual labels only."""
    return apply_manual_labels(pair=pair, expected_timeframe=expected_timeframe)
