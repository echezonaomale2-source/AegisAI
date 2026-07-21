"""Post-trade review engine — compare prediction vs reality with research scorecard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.decision_schemas import TradeDecision
from research.decision_quality import DecisionQualityClassifier
from research.models import ResearchScorecard, ReviewReport


class PostTradeReviewEngine:
    """
    Every completed trade triggers a review comparing original analysis
    to outcome. Decision quality is scored independently of win/loss.
    """

    def __init__(self) -> None:
        self.quality = DecisionQualityClassifier()

    def review(
        self,
        trade_id: str,
        *,
        outcome: str,
        decision: TradeDecision,
        outcome_chart: Path | None = None,
        cognitive_archive: dict[str, Any] | None = None,
        legacy_review: dict[str, Any] | None = None,
    ) -> ReviewReport:
        won = outcome.upper() in {"TAKE_PROFIT", "TP"}
        a4 = decision.analysis_4h
        a1 = decision.analysis_1h
        a15 = decision.analysis_15m

        htf_ok = self._htf_bias_assessment(decision, won)
        m15_ok = self._m15_confirmation(decision)
        liq_ok = a4.liquidity_sweep or a1.liquidity_sweep or a15.liquidity_sweep or (
            a4.liquidity not in {"None Detected", "Unknown", ""}
        )
        ob_ok = a4.bullish_order_block or a4.bearish_order_block or a1.bullish_order_block or a1.bearish_order_block
        fvg_ok = a4.fair_value_gap or a1.fair_value_gap or a15.fair_value_gap

        # Confidence appropriateness: did high confidence match success?
        conf = decision.confidence
        if conf >= 85:
            conf_appropriate = won
        elif conf >= 70:
            conf_appropriate = True  # mid band — not overclaiming
        else:
            conf_appropriate = decision.overall_bias == "NO TRADE" or not won

        should_no_trade = False
        if decision.overall_bias in {"BUY", "SELL"}:
            # Weak structure / conflicts → should have been NO TRADE (process judgment)
            weak_structure = a4.market_structure in {"Unknown", ""} or a1.market_structure in {"Unknown", ""}
            if weak_structure or conf < 70:
                should_no_trade = True
            if cognitive_archive:
                reasoning = (cognitive_archive.get("reasoning") or {})
                if reasoning.get("conclusion") == "NO TRADE":
                    should_no_trade = True

        scorecard = self._build_scorecard(
            decision,
            won=won,
            htf_ok=htf_ok,
            m15_ok=m15_ok,
            liq_ok=bool(liq_ok),
            ob_ok=bool(ob_ok),
            fvg_ok=bool(fvg_ok),
            conf_appropriate=bool(conf_appropriate),
            should_no_trade=should_no_trade,
            legacy_review=legacy_review,
        )
        # Overall from process metrics only — do not bake win/loss into quality label.
        quality = self.quality.classify(scorecard)

        strengths: list[str] = []
        weaknesses: list[str] = []
        if htf_ok:
            strengths.append("Higher-timeframe bias assessment was coherent.")
        else:
            weaknesses.append("Higher-timeframe bias was questionable relative to outcome context.")
        if m15_ok:
            strengths.append("15M confirmation signals were present.")
        else:
            weaknesses.append("15M confirmation was weak or missing.")
        if liq_ok:
            strengths.append("Liquidity was identified on at least one timeframe.")
        else:
            weaknesses.append("Liquidity identification was incomplete.")
        if ob_ok:
            strengths.append("Order block context was present.")
        else:
            weaknesses.append("Order block quality was limited.")
        if fvg_ok:
            strengths.append("FVG context contributed to the setup.")
        else:
            weaknesses.append("FVG was not a meaningful part of the thesis.")
        if conf_appropriate:
            strengths.append("Confidence level was appropriate for the evidence.")
        else:
            weaknesses.append("Confidence was misaligned with setup quality / outcome.")
        if should_no_trade:
            weaknesses.append("Evidence suggests NO TRADE would have been more appropriate.")

        questions = {
            "Was the higher-timeframe bias correct?": _yn(htf_ok),
            "Was the 15M confirmation valid?": _yn(m15_ok),
            "Was liquidity identified correctly?": _yn(liq_ok),
            "Was the Order Block respected?": _yn(ob_ok),
            "Was the FVG meaningful?": _yn(fvg_ok),
            "Was the confidence appropriate?": _yn(conf_appropriate),
            "Should the AI have recommended NO TRADE?": "Yes" if should_no_trade else "No",
        }

        summary = (
            f"Review {trade_id}: outcome {outcome}, decision quality {quality}, "
            f"overall analysis {scorecard.overall_analysis_quality:.0f}%. "
            f"Bias was {decision.overall_bias} at {conf:.0f}% confidence."
        )

        return ReviewReport(
            trade_id=trade_id,
            outcome=outcome,
            htf_bias_correct=htf_ok,
            m15_confirmation_valid=m15_ok,
            liquidity_identified_correctly=bool(liq_ok),
            order_block_respected=bool(ob_ok),
            fvg_meaningful=bool(fvg_ok),
            confidence_appropriate=bool(conf_appropriate),
            should_have_been_no_trade=should_no_trade,
            strengths=strengths,
            weaknesses=weaknesses,
            scorecard=scorecard,
            decision_quality=quality,
            questions=questions,
            summary=summary,
            cognitive_hash=(cognitive_archive or {}).get("reproducible_hash")
            or (cognitive_archive or {}).get("cognitive_decision", {}).get("reproducible_hash"),
            metadata={"outcome_chart": str(outcome_chart) if outcome_chart else None},
        )

    def _htf_bias_assessment(self, decision: TradeDecision, won: bool) -> bool | None:
        bias = decision.overall_bias
        if bias == "NO TRADE":
            return True  # withholding is coherent process
        a4 = decision.analysis_4h
        if bias == "BUY":
            aligned = a4.trend == "Bullish" and a4.status == "ok"
        elif bias == "SELL":
            aligned = a4.trend == "Bearish" and a4.status == "ok"
        else:
            aligned = False
        # Process correctness of HTF read — not whether trade won.
        return aligned

    def _m15_confirmation(self, decision: TradeDecision) -> bool:
        m15 = decision.analysis_15m
        if decision.overall_bias == "NO TRADE":
            return True
        if m15.status != "ok":
            return False
        signals = 0
        if m15.bos:
            signals += 1
        if m15.choch:
            signals += 1
        if m15.liquidity_sweep:
            signals += 1
        if m15.bullish_order_block or m15.bearish_order_block:
            signals += 1
        if m15.fair_value_gap:
            signals += 1
        return signals >= 2

    def _build_scorecard(
        self,
        decision: TradeDecision,
        *,
        won: bool,
        htf_ok: bool | None,
        m15_ok: bool | None,
        liq_ok: bool,
        ob_ok: bool,
        fvg_ok: bool,
        conf_appropriate: bool,
        should_no_trade: bool,
        legacy_review: dict[str, Any] | None,
    ) -> ResearchScorecard:
        # Prefer legacy Phase 4.5 numeric scores when present (process fields).
        legacy_sc = (legacy_review or {}).get("scorecard") or {}

        def pick(key: str, fallback: float) -> float:
            val = legacy_sc.get(key)
            if isinstance(val, (int, float)):
                return float(val)
            return fallback

        htf = pick("higher_timeframe_alignment", 85.0 if htf_ok else 40.0)
        entry = pick("entry_quality", 70.0 if decision.entry not in {"—", None, ""} else 35.0)
        sl = pick("stop_loss_placement", 70.0 if decision.stop_loss not in {"—", None, ""} else 35.0)
        tp = pick("take_profit_placement", 70.0 if decision.take_profit not in {"—", None, ""} else 35.0)
        structure = pick(
            "market_structure",
            80.0
            if decision.analysis_4h.market_structure not in {"Unknown", ""}
            else 35.0,
        )
        liquidity = pick("liquidity", 80.0 if liq_ok else 40.0)
        ob = pick("order_block", 75.0 if ob_ok else 40.0)
        fvg = pick("fair_value_gap", 75.0 if fvg_ok else 40.0)

        # Calibration score: process — was confidence claim justified?
        calib = 85.0 if conf_appropriate else 45.0
        if should_no_trade and decision.overall_bias in {"BUY", "SELL"}:
            calib = min(calib, 40.0)
            entry = min(entry, 45.0)

        parts = [htf, entry, sl, tp, structure, liquidity, ob, fvg, calib]
        overall = sum(parts) / len(parts)

        # Explicitly do NOT boost overall for wins or penalize for losses here.
        _ = won

        return ResearchScorecard(
            higher_timeframe_alignment=round(htf, 1),
            entry_quality=round(entry, 1),
            stop_loss_placement=round(sl, 1),
            take_profit_placement=round(tp, 1),
            market_structure_detection=round(structure, 1),
            liquidity_detection=round(liquidity, 1),
            order_block_quality=round(ob, 1),
            fvg_quality=round(fvg, 1),
            confidence_calibration=round(calib, 1),
            overall_analysis_quality=round(overall, 1),
        )


def _yn(value: bool | None) -> str:
    if value is None:
        return "Unknown"
    return "Yes" if value else "No"
