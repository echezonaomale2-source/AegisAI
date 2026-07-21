"""Top-down Smart Money Concepts decision engine."""

from __future__ import annotations

from models.chart_schemas import ChartAnalysis, MultiChartAnalysis
from models.decision_schemas import TradeDecision, TradeDirection
from models.schemas import utc_now_iso
from .confidence_engine import MIN_CONFIDENCE_THRESHOLD, ConfidenceEngine
from .explanation_engine import ExplanationEngine
from .risk_engine import RiskEngine


def _is_bullish(analysis: ChartAnalysis) -> bool:
    return analysis.status == "ok" and analysis.trend == "Bullish"


def _is_bearish(analysis: ChartAnalysis) -> bool:
    return analysis.status == "ok" and analysis.trend == "Bearish"


def _has_structure(analysis: ChartAnalysis) -> bool:
    return (
        analysis.status == "ok"
        and analysis.market_structure not in {"Unknown", ""}
        and analysis.swing_high_count + analysis.swing_low_count >= 2
    )


def _liquidity_clear(analysis: ChartAnalysis) -> bool:
    if analysis.status != "ok":
        return False
    if analysis.liquidity_sweep:
        return True
    if analysis.equal_highs or analysis.equal_lows:
        return True
    if analysis.liquidity not in {"None Detected", "Unknown", ""}:
        return True
    return False


def _bullish_15m_confirmation(m15: ChartAnalysis) -> bool:
    if m15.status != "ok" or m15.trend == "Bearish":
        return False
    signals = 0
    if m15.bos:
        signals += 1
    if m15.choch:
        signals += 1
    if m15.liquidity_sweep:
        signals += 1
    if m15.bullish_order_block:
        signals += 1
    if m15.fair_value_gap and m15.fvg_type == "Bullish FVG":
        signals += 1
    if m15.strong_rejection or m15.weak_rejection:
        signals += 1
    if m15.trend == "Bullish":
        signals += 1
    return signals >= 2


def _bearish_15m_confirmation(m15: ChartAnalysis) -> bool:
    if m15.status != "ok" or m15.trend == "Bullish":
        return False
    signals = 0
    if m15.bos:
        signals += 1
    if m15.choch:
        signals += 1
    if m15.liquidity_sweep:
        signals += 1
    if m15.bearish_order_block:
        signals += 1
    if m15.fair_value_gap and m15.fvg_type == "Bearish FVG":
        signals += 1
    if m15.strong_rejection or m15.weak_rejection:
        signals += 1
    if m15.trend == "Bearish":
        signals += 1
    return signals >= 2


def _resolve_pair(h4: ChartAnalysis, h1: ChartAnalysis, m15: ChartAnalysis, fallback: str) -> str:
    for chart in (h4, h1, m15):
        if chart.pair and chart.pair != "Unknown":
            return chart.pair
    clean = (fallback or "").strip().upper()
    if clean and clean != "UNKNOWN":
        return clean
    return "Unknown"


class DecisionEngine:
    def __init__(self) -> None:
        try:
            from memory.learning_engine import LearningEngine

            adaptive = LearningEngine().get_adaptive_weights()
        except Exception:
            adaptive = None
        self.confidence_engine = ConfidenceEngine(weights=adaptive)
        self.risk_engine = RiskEngine()
        self.explanation_engine = ExplanationEngine()

    def decide(
        self,
        multi: MultiChartAnalysis,
        *,
        pair_hint: str = "Unknown",
    ) -> TradeDecision:
        h4 = multi.chart_4h
        h1 = multi.chart_1h
        m15 = multi.chart_15m
        warnings: list[str] = []
        no_trade_reasons: list[str] = []

        # --- Quality gates ---
        for label, chart in (("4H", h4), ("1H", h1), ("15M", m15)):
            if chart.status != "ok":
                no_trade_reasons.append(
                    f"{label} image quality/analysis failed: {chart.error or 'Image Quality Too Low'}."
                )

        if no_trade_reasons:
            return self._finalize(
                h4=h4,
                h1=h1,
                m15=m15,
                pair_hint=pair_hint,
                direction="NO TRADE",
                no_trade_reasons=no_trade_reasons,
                warnings=warnings,
            )

        # --- Structure gates ---
        if not _has_structure(h4):
            no_trade_reasons.append("Missing market structure on 4H.")
        if not _has_structure(h1):
            no_trade_reasons.append("Missing market structure on 1H.")
        if not _has_structure(m15):
            no_trade_reasons.append("Missing market structure on 15M.")

        # --- Liquidity clarity (at least one HTF/MTF liquidity read) ---
        if not (_liquidity_clear(h4) or _liquidity_clear(h1) or _liquidity_clear(m15)):
            no_trade_reasons.append("Unclear liquidity across timeframes.")
            warnings.append("Liquidity map is weak — professional entries require clearer pools.")

        # --- Top-down bias ---
        candidate: TradeDirection | None = None
        if _is_bullish(h4) and _is_bullish(h1):
            if _bullish_15m_confirmation(m15):
                candidate = "BUY"
            else:
                no_trade_reasons.append("Missing 15M bullish confirmation.")
        elif _is_bearish(h4) and _is_bearish(h1):
            if _bearish_15m_confirmation(m15):
                candidate = "SELL"
            else:
                no_trade_reasons.append("Missing 15M bearish confirmation.")
        else:
            no_trade_reasons.append("Higher timeframe conflict or non-trending HTF bias.")
            if h4.trend != h1.trend:
                no_trade_reasons.append(
                    f"4H trend ({h4.trend}) disagrees with 1H trend ({h1.trend})."
                )

        # 1H continuation / retracement context notes (warnings, not auto-entries)
        if candidate == "BUY" and h1.correction_move:
            warnings.append("1H shows corrective movement — wait for fresh 15M confirmation candle.")
        if candidate == "SELL" and h1.correction_move:
            warnings.append("1H shows corrective movement — wait for fresh 15M confirmation candle.")

        scorecard = self.confidence_engine.score(
            h4=h4,
            h1=h1,
            m15=m15,
            candidate_direction=candidate,
        )

        if candidate is None:
            return self._finalize(
                h4=h4,
                h1=h1,
                m15=m15,
                pair_hint=pair_hint,
                direction="NO TRADE",
                no_trade_reasons=no_trade_reasons or ["No valid top-down alignment."],
                warnings=warnings,
                scorecard=scorecard,
            )

        if scorecard.overall < MIN_CONFIDENCE_THRESHOLD:
            no_trade_reasons.append(
                f"Weak confidence {scorecard.overall:.0f}% "
                f"(minimum {MIN_CONFIDENCE_THRESHOLD:.0f}%)."
            )
            return self._finalize(
                h4=h4,
                h1=h1,
                m15=m15,
                pair_hint=pair_hint,
                direction="NO TRADE",
                no_trade_reasons=no_trade_reasons,
                warnings=warnings,
                scorecard=scorecard,
            )

        if no_trade_reasons:
            # Structure/liquidity blockers still apply even if candidate formed.
            return self._finalize(
                h4=h4,
                h1=h1,
                m15=m15,
                pair_hint=pair_hint,
                direction="NO TRADE",
                no_trade_reasons=no_trade_reasons,
                warnings=warnings,
                scorecard=scorecard,
            )

        risk = self.risk_engine.build(direction=candidate, h4=h4, h1=h1, m15=m15)
        if risk.trade_direction == "NO TRADE":
            return self._finalize(
                h4=h4,
                h1=h1,
                m15=m15,
                pair_hint=pair_hint,
                direction="NO TRADE",
                no_trade_reasons=risk.notes or ["Risk engine rejected the setup."],
                warnings=warnings,
                scorecard=scorecard,
                risk=risk,
            )

        return self._finalize(
            h4=h4,
            h1=h1,
            m15=m15,
            pair_hint=pair_hint,
            direction=candidate,
            no_trade_reasons=[],
            warnings=warnings,
            scorecard=scorecard,
            risk=risk,
        )

    def _finalize(
        self,
        *,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        pair_hint: str,
        direction: TradeDirection,
        no_trade_reasons: list[str],
        warnings: list[str],
        scorecard=None,
        risk=None,
    ) -> TradeDecision:
        if scorecard is None:
            scorecard = self.confidence_engine.score(
                h4=h4,
                h1=h1,
                m15=m15,
                candidate_direction=None if direction == "NO TRADE" else direction,
            )
        if risk is None:
            risk = self.risk_engine.build(direction=direction, h4=h4, h1=h1, m15=m15)

        explanation, reasons = self.explanation_engine.build(
            direction=direction,
            h4=h4,
            h1=h1,
            m15=m15,
            scorecard=scorecard,
            risk=risk,
            no_trade_reasons=no_trade_reasons,
        )

        return TradeDecision(
            pair=_resolve_pair(h4, h1, m15, pair_hint),
            timeframes={
                "4H": h4.timeframe if h4.timeframe != "Unknown" else "4H",
                "1H": h1.timeframe if h1.timeframe != "Unknown" else "1H",
                "15M": m15.timeframe if m15.timeframe != "Unknown" else "15M",
            },
            analysis_4h=h4,
            analysis_1h=h1,
            analysis_15m=m15,
            overall_bias=direction,
            entry=risk.entry if direction != "NO TRADE" else "—",
            stop_loss=risk.stop_loss if direction != "NO TRADE" else "—",
            take_profit=risk.take_profit if direction != "NO TRADE" else "—",
            risk_reward=risk.risk_reward if direction != "NO TRADE" else "—",
            target_liquidity=risk.target_liquidity if direction != "NO TRADE" else "None",
            confidence=scorecard.overall,
            confidence_scorecard=scorecard,
            explanation=explanation,
            reasons=reasons,
            warnings=warnings,
            status="Waiting Result",
            generated_at=utc_now_iso(),
        )
