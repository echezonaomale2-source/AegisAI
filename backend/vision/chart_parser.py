"""Parse pair and timeframe labels from chart screenshot chrome."""

from __future__ import annotations

import re
from dataclasses import dataclass

import cv2
import numpy as np

KNOWN_PAIRS = {
    "EURUSD": ["EURUSD", "EUR/USD", "EUR USD", "EURUSD."],
    "GBPUSD": ["GBPUSD", "GBP/USD", "GBP USD"],
    "USDJPY": ["USDJPY", "USD/JPY", "USD JPY"],
    "XAUUSD": ["XAUUSD", "XAU/USD", "GOLD", "XAU USD"],
    "BTCUSD": ["BTCUSD", "BTC/USD", "BTCUSD.", "BITCOIN", "BTC"],
}

TIMEFRAME_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("1M", re.compile(r"\b(?:M1|1\s*M|1\s*MIN|1\s*MINUTE)\b", re.I)),
    ("5M", re.compile(r"\b(?:M5|5\s*M|5\s*MIN)\b", re.I)),
    ("15M", re.compile(r"\b(?:M15|15\s*M|15\s*MIN|15\s*MINUTE)\b", re.I)),
    ("30M", re.compile(r"\b(?:M30|30\s*M|30\s*MIN)\b", re.I)),
    ("1H", re.compile(r"\b(?:H1|1\s*H|60\s*M|1\s*HOUR)\b", re.I)),
    ("4H", re.compile(r"\b(?:H4|4\s*H|240\s*M|4\s*HOUR)\b", re.I)),
    ("1D", re.compile(r"\b(?:D1|1\s*D|DAILY|1\s*DAY)\b", re.I)),
    ("1W", re.compile(r"\b(?:W1|1\s*W|WEEKLY)\b", re.I)),
]

SESSION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("London", re.compile(r"\bLONDON\b", re.I)),
    ("New York", re.compile(r"\b(?:NEW\s*YORK|NY|NEWYORK)\b", re.I)),
    ("Asian", re.compile(r"\b(?:ASIAN|TOKYO|ASIA)\b", re.I)),
    ("Sydney", re.compile(r"\bSYDNEY\b", re.I)),
]


@dataclass
class ChartLabels:
    pair: str
    timeframe: str
    detected_timeframe_label: str | None
    session_labels: list[str]
    pair_confidence: float
    timeframe_confidence: float
    raw_text: str


def _ocr_text(image: np.ndarray) -> str:
    try:
        import pytesseract
    except ImportError:
        return ""

    try:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
        upscaled = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
        _, thresh = cv2.threshold(upscaled, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        inverted = 255 - thresh
        configs = [
            "--psm 6",
            "--psm 11",
            "--psm 7",
        ]
        chunks: list[str] = []
        for config in configs:
            try:
                text = pytesseract.image_to_string(inverted, config=config)
                if text and text.strip():
                    chunks.append(text)
            except Exception:
                continue
        return "\n".join(chunks)
    except Exception:
        return ""


def _detect_pair(text: str) -> tuple[str, float]:
    normalized = text.upper().replace("-", "").replace("_", " ")
    compact = re.sub(r"[^A-Z0-9/ ]", " ", normalized)
    for pair, aliases in KNOWN_PAIRS.items():
        for alias in aliases:
            if alias.upper() in compact or alias.upper().replace(" ", "") in compact.replace(" ", ""):
                return pair, 90.0
    # Generic 6-letter FX pair pattern — only report if clearly present.
    match = re.search(r"\b([A-Z]{3}\s*/?\s*[A-Z]{3})\b", compact)
    if match:
        token = re.sub(r"[^A-Z]", "", match.group(1))
        if len(token) == 6:
            return token, 75.0
    return "Unknown", 0.0


def _detect_timeframe(text: str) -> tuple[str, str | None, float]:
    for label, pattern in TIMEFRAME_PATTERNS:
        match = pattern.search(text)
        if match:
            return label, match.group(0), 88.0
    return "Unknown", None, 0.0


def _detect_sessions(text: str) -> list[str]:
    found: list[str] = []
    for label, pattern in SESSION_PATTERNS:
        if pattern.search(text):
            found.append(label)
    return found


def parse_chart_labels(full_bgr: np.ndarray, expected_timeframe: str | None = None) -> ChartLabels:
    """
    Read pair/timeframe from screenshot chrome.
    Never guesses — returns Unknown when evidence is missing.
    """
    height, width = full_bgr.shape[:2]
    # Header + left legend typically contain symbol / TF.
    regions = [
        full_bgr[0 : max(int(height * 0.14), 40), :],
        full_bgr[0 : max(int(height * 0.22), 60), 0 : max(int(width * 0.45), 120)],
    ]
    texts = [_ocr_text(region) for region in regions]
    raw = "\n".join(t for t in texts if t).strip()

    pair, pair_conf = _detect_pair(raw) if raw else ("Unknown", 0.0)
    timeframe, tf_label, tf_conf = _detect_timeframe(raw) if raw else ("Unknown", None, 0.0)
    sessions = _detect_sessions(raw) if raw else []

    # If OCR found nothing for timeframe, keep Unknown (do not assume expected).
    # Report mismatch note via detected_timeframe_label when expected differs.
    detected_label = tf_label
    if (
        expected_timeframe
        and timeframe != "Unknown"
        and timeframe.upper() != expected_timeframe.upper()
    ):
        detected_label = f"{timeframe} (expected {expected_timeframe})"

    return ChartLabels(
        pair=pair,
        timeframe=timeframe,
        detected_timeframe_label=detected_label,
        session_labels=sessions,
        pair_confidence=pair_conf,
        timeframe_confidence=tf_conf,
        raw_text=raw[:500],
    )
