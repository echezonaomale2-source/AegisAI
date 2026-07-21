"""Post-trade review engine — prediction vs reality case study."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from models.chart_schemas import ChartAnalysis
from models.decision_schemas import TradeDecision
from services.chart_analysis_service import ChartAnalysisService


@dataclass
class ReviewScorecard:
    market_structure_accuracy: float
    liquidity_detection_accuracy: float
    order_block_quality: float
    fvg_quality: float
    entry_quality: float
    stop_loss_placement: float
    take_profit_placement: float
    risk_reward_quality: float
    overall_analysis_quality: float

    def as_dict(self) -> dict[str, float]:
        return {
            "market_structure_accuracy": round(self.market_structure_accuracy, 1),
            "liquidity_detection_accuracy": round(self.liquidity_detection_accuracy, 1),
            "order_block_quality": round(self.order_block_quality, 1),
            "fvg_quality": round(self.fvg_quality, 1),
            "entry_quality": round(self.entry_quality, 1),
            "stop_loss_placement": round(self.stop_loss_placement, 1),
            "take_profit_placement": round(self.take_profit_placement, 1),
            "risk_reward_quality": round(self.risk_reward_quality, 1),
            "overall_analysis_quality": round(self.overall_analysis_quality, 1),
        }


@dataclass
class SelfCritique:
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    improvements: list[str] = field(default_factory=list)
    answers: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "improvements": self.improvements,
            "answers": self.answers,
        }


@dataclass
class TradeReview:
    scorecard: ReviewScorecard
    critique: SelfCritique
    grade: str
    outcome_analysis: ChartAnalysis | None
    questions: dict[str, str]
    summary: str

    def as_dict(self) -> dict:
        return {
            "scorecard": self.scorecard.as_dict(),
            "critique": self.critique.as_dict(),
            "grade": self.grade,
            "questions": self.questions,
            "summary": self.summary,
            "outcome_analysis": (
                self.outcome_analysis.model_dump() if self.outcome_analysis else None
            ),
        }


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _safe_float(value: str | None) -> float | None:
    if value is None or value in {"—", "-", ""}:
        return None
    try:
        return float(str(value).replace(",", ""))
    except ValueError:
        return None


def grade_from_score(overall: float) -> str:
    if overall >= 92:
        return "A+"
    if overall >= 85:
        return "A"
    if overall >= 75:
        return "B"
    if overall >= 65:
        return "C"
    if overall >= 50:
        return "D"
    return "F"


class ReviewEngine:
    """
    Case-study review after every completed trade.

    Does not learn blindly from TP/SL — scores whether the original reasoning
    held up against the final chart and outcome.
    """

    def __init__(self) -> None:
        self.chart_service = ChartAnalysisService()

    def review(
        self,
        decision: TradeDecision,
        *,
        outcome: str,
        outcome_chart_path: str | None,
    ) -> TradeReview:
        outcome_analysis: ChartAnalysis | None = None
        if outcome_chart_path and Path(outcome_chart_path).exists():
            try:
                outcome_analysis = self.chart_service.analyze(outcome_chart_path)
            except Exception:
                outcome_analysis = None

        h4 = decision.analysis_4h
        h1 = decision.analysis_1h
        m15 = decision.analysis_15m
        direction = decision.overall_bias
        won = outcome == "TAKE_PROFIT"

        structure = self._score_structure(h4, h1, m15, direction, outcome_analysis, won)
        liquidity = self._score_liquidity(h4, h1, m15, outcome_analysis, won)
        ob = self._score_order_blocks(h4, h1, m15, direction, won)
        fvg = self._score_fvg(h4, h1, m15, direction, won)
        entry = self._score_entry(decision, m15, direction, won)
        stop = self._score_stop(decision, direction, won)
        take = self._score_take(decision, direction, won)
        rr = self._score_rr(decision, won)

        overall = (
            structure * 0.15
            + liquidity * 0.12
            + ob * 0.12
            + fvg * 0.10
            + entry * 0.15
            + stop * 0.12
            + take * 0.12
            + rr * 0.12
        )
        # NO TRADE that avoided a loss is high-quality process.
        if direction == "NO TRADE":
            overall = max(overall, 78.0)
            structure = max(structure, 75.0)

        scorecard = ReviewScorecard(
            market_structure_accuracy=_clamp(structure),
            liquidity_detection_accuracy=_clamp(liquidity),
            order_block_quality=_clamp(ob),
            fvg_quality=_clamp(fvg),
            entry_quality=_clamp(entry),
            stop_loss_placement=_clamp(stop),
            take_profit_placement=_clamp(take),
            risk_reward_quality=_clamp(rr),
            overall_analysis_quality=_clamp(overall),
        )
        grade = grade_from_score(scorecard.overall_analysis_quality)
        critique = self._critique(decision, outcome, outcome_analysis, scorecard, won)
        questions = self._answer_questions(decision, outcome, outcome_analysis, scorecard, won)
        summary = (
            f"Grade {grade}. Overall analysis quality "
            f"{scorecard.overall_analysis_quality:.0f}/100. "
            f"Outcome: {outcome.replace('_', ' ')}."
        )
        return TradeReview(
            scorecard=scorecard,
            critique=critique,
            grade=grade,
            outcome_analysis=outcome_analysis if outcome_analysis and outcome_analysis.status == "ok" else None,
            questions=questions,
            summary=summary,
        )

    def _score_structure(
        self,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        direction: str,
        outcome: ChartAnalysis | None,
        won: bool,
    ) -> float:
        score = 45.0
        if h4.trend == h1.trend and h4.trend in {"Bullish", "Bearish"}:
            score += 20.0
        if m15.bos or m15.choch:
            score += 12.0
        if direction == "BUY" and h4.trend == "Bullish":
            score += 10.0
        if direction == "SELL" and h4.trend == "Bearish":
            score += 10.0
        if outcome and outcome.status == "ok":
            if direction == "BUY" and outcome.trend == "Bullish":
                score += 10.0
            elif direction == "SELL" and outcome.trend == "Bearish":
                score += 10.0
            elif direction in {"BUY", "SELL"} and outcome.trend not in {None, "Unknown", "Range"}:
                if (direction == "BUY" and outcome.trend == "Bearish") or (
                    direction == "SELL" and outcome.trend == "Bullish"
                ):
                    score -= 18.0 if not won else 6.0
        if not won and direction in {"BUY", "SELL"}:
            score -= 8.0
        if won:
            score += 8.0
        return score

    def _score_liquidity(
        self,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        outcome: ChartAnalysis | None,
        won: bool,
    ) -> float:
        score = 40.0
        if h4.liquidity_sweep or h1.liquidity_sweep or m15.liquidity_sweep:
            score += 25.0
        if h4.equal_highs or h4.equal_lows or h1.equal_highs or h1.equal_lows:
            score += 12.0
        if any(c.liquidity not in {"None Detected", "Unknown", ""} for c in (h4, h1, m15)):
            score += 10.0
        if outcome and outcome.status == "ok" and outcome.liquidity_sweep:
            score += 8.0
        if won:
            score += 5.0
        else:
            score -= 5.0
        return score

    def _score_order_blocks(
        self,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        direction: str,
        won: bool,
    ) -> float:
        score = 35.0
        aligned = False
        if direction == "BUY" and (h1.bullish_order_block or m15.bullish_order_block or h4.bullish_order_block):
            aligned = True
            score += 30.0
        if direction == "SELL" and (h1.bearish_order_block or m15.bearish_order_block or h4.bearish_order_block):
            aligned = True
            score += 30.0
        if direction == "BUY" and m15.bearish_order_block:
            score -= 15.0
        if direction == "SELL" and m15.bullish_order_block:
            score -= 15.0
        if aligned and won:
            score += 15.0
        if aligned and not won:
            score -= 10.0  # OB present but failed — quality question
        if not aligned:
            score += 5.0  # neutral if unused
        return score

    def _score_fvg(
        self,
        h4: ChartAnalysis,
        h1: ChartAnalysis,
        m15: ChartAnalysis,
        direction: str,
        won: bool,
    ) -> float:
        score = 40.0
        wanted = "Bullish FVG" if direction == "BUY" else "Bearish FVG" if direction == "SELL" else None
        has = any(c.fair_value_gap for c in (h4, h1, m15))
        aligned = any(c.fvg_type == wanted for c in (h4, h1, m15)) if wanted else False
        if aligned:
            score += 30.0
            score += 15.0 if won else -12.0
        elif has:
            score += 5.0
            score -= 8.0 if not won else 0.0
        else:
            score += 10.0  # FVG not required
        return score

    def _score_entry(self, decision: TradeDecision, m15: ChartAnalysis, direction: str, won: bool) -> float:
        if direction == "NO TRADE":
            return 85.0
        score = 40.0
        if m15.bos or m15.choch:
            score += 15.0
        if m15.liquidity_sweep:
            score += 12.0
        if m15.strong_rejection:
            score += 10.0
        conf = decision.confidence
        if conf >= 80:
            score += 10.0
        elif conf < 70:
            score -= 10.0
        score += 15.0 if won else -18.0
        return score

    def _score_stop(self, decision: TradeDecision, direction: str, won: bool) -> float:
        if direction == "NO TRADE":
            return 80.0
        entry = _safe_float(decision.entry)
        stop = _safe_float(decision.stop_loss)
        score = 55.0
        if entry is None or stop is None:
            return 35.0
        risk = abs(entry - stop)
        if risk <= 0:
            return 20.0
        # Reasonable stop distance relative to RR text if available
        score += 15.0
        if won:
            score += 20.0  # stop held
        else:
            score -= 5.0  # may have been tight or thesis wrong
            if risk < 0.5:
                score -= 15.0  # likely too tight on chart scale
                score -= 5.0
        return score

    def _score_take(self, decision: TradeDecision, direction: str, won: bool) -> float:
        if direction == "NO TRADE":
            return 80.0
        entry = _safe_float(decision.entry)
        take = _safe_float(decision.take_profit)
        score = 50.0
        if entry is None or take is None:
            return 30.0
        if abs(take - entry) > 0:
            score += 20.0
        score += 25.0 if won else -10.0
        return score

    def _score_rr(self, decision: TradeDecision, won: bool) -> float:
        rr = _safe_float(decision.risk_reward)
        score = 45.0
        if rr is None:
            return 30.0
        if rr >= 3:
            score += 30.0
        elif rr >= 2:
            score += 22.0
        elif rr >= 1.5:
            score += 12.0
        else:
            score -= 15.0
        score += 10.0 if won else -5.0
        return score

    def _critique(
        self,
        decision: TradeDecision,
        outcome: str,
        outcome_analysis: ChartAnalysis | None,
        scorecard: ReviewScorecard,
        won: bool,
    ) -> SelfCritique:
        strengths: list[str] = []
        weaknesses: list[str] = []
        improvements: list[str] = []
        h4, h1, m15 = decision.analysis_4h, decision.analysis_1h, decision.analysis_15m

        if h4.trend == h1.trend and h4.trend in {"Bullish", "Bearish"}:
            strengths.append(f"Correctly detected {h4.trend.lower()} higher-timeframe trend alignment.")
        if h1.liquidity_sweep or m15.liquidity_sweep:
            strengths.append("Liquidity sweep identification was present in the thesis.")
        if m15.bos or m15.choch:
            strengths.append("Lower-timeframe BOS/CHOCH confirmation was part of the plan.")
        if decision.overall_bias == "NO TRADE":
            strengths.append("Correctly withheld a forced trade when evidence was insufficient.")
        if won and scorecard.overall_analysis_quality >= 75:
            strengths.append("Prediction aligned with realized outcome at acceptable quality.")

        if scorecard.entry_quality < 60:
            weaknesses.append("Entry quality scored weak — timing may have been early or poorly confirmed.")
            improvements.append("Require clearer 15M confirmation candle before entry.")
        if scorecard.stop_loss_placement < 60:
            weaknesses.append("Stop loss placement scored weak — possibly too tight or poorly anchored.")
            improvements.append("Anchor stops beyond invalidation of the protected swing / order block.")
        if scorecard.order_block_quality < 55:
            weaknesses.append("Order block quality was questionable or opposing OB was ignored.")
        if scorecard.fvg_quality < 55:
            weaknesses.append("Fair value gap contribution was weak or overweighted.")
            improvements.append("Treat FVG as confluence only — never as a standalone entry.")
        if not won and decision.confidence >= 80:
            weaknesses.append("Confidence should have been lower relative to the eventual invalidation.")
            improvements.append("Reduce confidence when liquidity is unclear or HTF alignment is soft.")
        if outcome_analysis and outcome_analysis.status == "ok":
            if decision.overall_bias == "BUY" and outcome_analysis.trend == "Bearish":
                weaknesses.append("Final chart trend conflicted with the original bullish thesis.")
            if decision.overall_bias == "SELL" and outcome_analysis.trend == "Bullish":
                weaknesses.append("Final chart trend conflicted with the original bearish thesis.")

        if not strengths:
            strengths.append("Case captured for permanent review even where strengths were limited.")
        if not weaknesses:
            weaknesses.append("No major structural weaknesses isolated in this case study.")
        if not improvements:
            improvements.append("Continue requiring multi-timeframe alignment before execution.")

        return SelfCritique(strengths=strengths, weaknesses=weaknesses, improvements=improvements)

    def _answer_questions(
        self,
        decision: TradeDecision,
        outcome: str,
        outcome_analysis: ChartAnalysis | None,
        scorecard: ReviewScorecard,
        won: bool,
    ) -> dict[str, str]:
        def yn(ok: bool, yes: str, no: str) -> str:
            return yes if ok else no

        direction = decision.overall_bias
        return {
            "Was my market analysis correct?": yn(
                scorecard.market_structure_accuracy >= 65,
                "Mostly yes — structure scoring supports the original read.",
                "Partially/No — market structure accuracy was weak versus the outcome.",
            ),
            "Was my entry correct?": yn(
                scorecard.entry_quality >= 65,
                "Yes — entry quality met review standards.",
                "No — entry quality was below standard (timing/confirmation).",
            ),
            "Was my stop loss correct?": yn(
                scorecard.stop_loss_placement >= 65,
                "Yes — stop placement was reasonable for the thesis.",
                "No — stop placement needs improvement.",
            ),
            "Was my take profit realistic?": yn(
                scorecard.take_profit_placement >= 65,
                "Yes — take profit placement was realistic.",
                "No — take profit targeting was weak or unrealistic.",
            ),
            "Did I correctly identify liquidity?": yn(
                scorecard.liquidity_detection_accuracy >= 65,
                "Yes — liquidity detection held up.",
                "No — liquidity read was unclear or incorrect.",
            ),
            "Did I correctly identify BOS?": yn(
                decision.analysis_15m.bos or decision.analysis_4h.bos or decision.analysis_1h.bos,
                "BOS was identified in the original analysis.",
                "BOS was not clearly identified.",
            ),
            "Did I correctly identify CHOCH?": yn(
                decision.analysis_15m.choch or decision.analysis_1h.choch or decision.analysis_4h.choch,
                "CHOCH was identified in the original analysis.",
                "CHOCH was not clearly identified.",
            ),
            "Did I correctly identify Order Blocks?": yn(
                scorecard.order_block_quality >= 65,
                "Order block assessment was acceptable.",
                "Order block assessment was weak or misleading.",
            ),
            "Did I correctly identify Fair Value Gaps?": yn(
                scorecard.fvg_quality >= 65,
                "FVG assessment was acceptable.",
                "FVG assessment was weak or over-relied upon.",
            ),
            "What should I improve?": (
                "; ".join(self._critique(decision, outcome, outcome_analysis, scorecard, won).improvements[:2])
                or "Maintain discipline on top-down confirmation."
            ),
            "Outcome context": f"{direction} → {outcome}; grade path based on review scorecard.",
        }
