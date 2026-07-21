"""Normalize trade outcomes for learning (TP / SL / BREAK_EVEN)."""

from __future__ import annotations

CLOSED_OUTCOMES = frozenset({"TAKE_PROFIT", "STOP_LOSS", "BREAK_EVEN", "TP", "SL", "BE"})
WIN_OUTCOMES = frozenset({"TAKE_PROFIT", "TP"})
LOSS_OUTCOMES = frozenset({"STOP_LOSS", "SL"})
NEUTRAL_OUTCOMES = frozenset({"BREAK_EVEN", "BE"})


def normalize_outcome(outcome: str) -> str:
    raw = (outcome or "").strip().upper()
    if raw in {"TP", "TAKE_PROFIT"}:
        return "TAKE_PROFIT"
    if raw in {"SL", "STOP_LOSS"}:
        return "STOP_LOSS"
    if raw in {"BE", "BREAK_EVEN"}:
        return "BREAK_EVEN"
    return raw


def is_win(outcome: str) -> bool:
    return normalize_outcome(outcome) in WIN_OUTCOMES


def is_loss(outcome: str) -> bool:
    return normalize_outcome(outcome) in LOSS_OUTCOMES


def is_neutral(outcome: str) -> bool:
    return normalize_outcome(outcome) in NEUTRAL_OUTCOMES


def counts_toward_calibration(outcome: str) -> bool:
    """Break-even is not a win or loss for confidence calibration."""
    return not is_neutral(outcome)


def status_code(outcome: str) -> str:
    o = normalize_outcome(outcome)
    if o == "TAKE_PROFIT":
        return "TP"
    if o == "BREAK_EVEN":
        return "BE"
    return "SL"
