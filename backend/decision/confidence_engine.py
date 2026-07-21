"""Weighted confidence scoring for top-down SMC decisions."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import ConfidenceScorecard

# Required weights (must sum to 1.0).
WEIGHTS = {
    "htf_4h_alignment": 0.30,
    "mtf_1h_alignment": 0.25,
    "ltf_15m_confirmation": 0.20,
    "liquidity": 0.10,
    "order_block": 0.05,
    "fair_value_gap": 0.05,
    "market_structure": 0.05,
}

MIN_CONFIDENCE_THRESHOLD = 70.0


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, float(value)))


def _trend_alignment_score(analysis: ChartAnalysis, expected: str | None) -> float:
    if analysis.status != "ok":
        return 0.0
    if analysis.trend == "Unknown":
        return 10.0
    if expected is None:
        if analysis.trend in {"Bullish", "Bearish"}:
            return 75.0 + (10.0 if analysis.bos else 0.0)
        return 40.0  # Range
    if analysis.trend == expected:
        score = 80.0
        if analysis.bos:
            score += 8.0
        if analysis.impulse_move:
            score += 5.0
        if expected == "Bullish" and analysis.discount == "Yes":
            score += 4.0
        if expected == "Bearish" and analysis.premium == "Yes":
            score += 4.0
        return _clamp(score)
    if analysis.trend == "Range":
        return 35.0
    return 5.0  # Conflict


def _confirmation_score(analysis: ChartAnalysis, direction: str | None) -> float:
    if analysis.status != "ok" or direction is None:
        return 0.0

    score = 20.0
    bullish_signals = 0
    bearish_signals = 0

    if analysis.bos:
        bullish_signals += 1 if direction == "BUY" else 0
        bearish_signals += 1 if direction == "SELL" else 0
        score += 15.0
    if analysis.choch:
        # CHOCH in trade direction is strong confirmation.
        if direction == "BUY" and analysis.trend in {"Bullish", "Range"}:
            bullish_signals += 1
            score += 18.0
        elif direction == "SELL" and analysis.trend in {"Bearish", "Range"}:
            bearish_signals += 1
            score += 18.0
    if analysis.liquidity_sweep:
        score += 12.0
    if direction == "BUY" and analysis.bullish_order_block:
        score += 10.0
        bullish_signals += 1
    if direction == "SELL" and analysis.bearish_order_block:
        score += 10.0
        bearish_signals += 1
    if direction == "BUY" and analysis.fvg_type == "Bullish FVG":
        score += 8.0
    if direction == "SELL" and analysis.fvg_type == "Bearish FVG":
        score += 8.0
    if analysis.strong_rejection:
        score += 10.0
    elif analysis.weak_rejection:
        score += 4.0

    if direction == "BUY" and bullish_signals == 0 and not analysis.bos and not analysis.choch:
        return _clamp(min(score, 45.0))
    if direction == "SELL" and bearish_signals == 0 and not analysis.bos and not analysis.choch:
        return _clamp(min(score, 45.0))
    return _clamp(score)


def _liquidity_score(h4: ChartAnalysis, h1: ChartAnalysis, m15: ChartAnalysis) -> float:
    score = 25.0
    for chart in (h4, h1, m15):
        if chart.status != "ok":
            continue
        if chart.liquidity_sweep:
            score += 18.0
        if chart.equal_highs or chart.equal_lows:
            score += 10.0
        if chart.liquidity not in {"None Detected", "Unknown", ""}:
            score += 8.0
        if chart.external_liquidity:
            score += 5.0
    return _clamp(score)


def _order_block_score(h4: ChartAnalysis, h1: ChartAnalysis, m15: ChartAnalysis, direction: str | None) -> float:
    if direction is None:
        return 20.0
    score = 15.0
    for chart in (h4, h1, m15):
        if chart.status != "ok":
            continue
        if direction == "BUY" and chart.bullish_order_block:
            score += 25.0
        if direction == "SELL" and chart.bearish_order_block:
            score += 25.0
    return _clamp(score)


def _fvg_score(h4: ChartAnalysis, h1: ChartAnalysis, m15: ChartAnalysis, direction: str | None) -> float:
    if direction is None:
        return 20.0
    score = 15.0
    wanted = "Bullish FVG" if direction == "BUY" else "Bearish FVG"
    for chart in (h4, h1, m15):
        if chart.status != "ok":
            continue
        if chart.fair_value_gap and chart.fvg_type == wanted:
            score += 25.0
        elif chart.fair_value_gap:
            score += 8.0
    return _clamp(score)


def _structure_score(h4: ChartAnalysis, h1: ChartAnalysis, m15: ChartAnalysis) -> float:
    score = 0.0
    count = 0
    for chart in (h4, h1, m15):
        if chart.status != "ok":
            continue
        count += 1
        if chart.market_structure not in {"Unknown", ""}:
            score += 70.0
        if chart.bos or chart.choch:
            score += 20.0
        if chart.swing_high_count >= 2 and chart.swing_low_count >= 2:
            score += 10.0
    if count == 0:
        return 0.0
    return _clamp(score / count)


class ConfidenceEngine:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = dict(weights or WEIGHTS)

    def score(
        self,
        *,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        candidate_direction: str | None,
    ) -> ConfidenceScorecard:
        expected_trend = None
        if candidate_direction == "BUY":
            expected_trend = "Bullish"
        elif candidate_direction == "SELL":
            expected_trend = "Bearish"

        weights = self.weights
        for key, value in WEIGHTS.items():
            weights.setdefault(key, value)
        total = sum(weights[k] for k in WEIGHTS)
        if total > 0:
            weights = {k: weights[k] / total for k in WEIGHTS}

        htf = _trend_alignment_score(h4, expected_trend)
        mtf = _trend_alignment_score(h1, expected_trend)
        ltf = _confirmation_score(m15, candidate_direction)
        liquidity = _liquidity_score(h4, h1, m15)
        order_block = _order_block_score(h4, h1, m15, candidate_direction)
        fvg = _fvg_score(h4, h1, m15, candidate_direction)
        structure = _structure_score(h4, h1, m15)

        overall = (
            htf * weights["htf_4h_alignment"]
            + mtf * weights["mtf_1h_alignment"]
            + ltf * weights["ltf_15m_confirmation"]
            + liquidity * weights["liquidity"]
            + order_block * weights["order_block"]
            + fvg * weights["fair_value_gap"]
            + structure * weights["market_structure"]
        )

        return ConfidenceScorecard(
            htf_4h_alignment=round(htf, 1),
            mtf_1h_alignment=round(mtf, 1),
            ltf_15m_confirmation=round(ltf, 1),
            liquidity=round(liquidity, 1),
            order_block=round(order_block, 1),
            fair_value_gap=round(fvg, 1),
            market_structure=round(structure, 1),
            overall=round(_clamp(overall), 1),
            weights={k: round(weights[k], 4) for k in WEIGHTS},
        )
