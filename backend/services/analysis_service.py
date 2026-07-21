"""App-facing analysis service — Phase 10 AI Brain entry point."""

from __future__ import annotations

from pathlib import Path

from brain.coordinator import AIBrain
from models.chart_schemas import ChartAnalysis
from models.decision_schemas import TradeDecision
from models.schemas import AnalysisResult, utc_now_iso


def _map_trend(trend: str) -> str:
    if trend == "Bullish":
        return "Bullish"
    if trend == "Bearish":
        return "Bearish"
    if trend == "Range":
        return "Consolidation"
    return "Consolidation"


def _map_structure(analysis: ChartAnalysis) -> str:
    if analysis.choch:
        return "Change Of Character"
    if analysis.bos:
        return "Break Of Structure"
    mapping = {
        "Higher Highs": "Higher High",
        "Higher High": "Higher High",
        "Higher Low": "Higher Low",
        "Lower Lows": "Lower Low",
        "Lower Low": "Lower Low",
        "Lower High": "Lower High",
    }
    return mapping.get(analysis.market_structure, "Neutral")


def _map_liquidity(analysis: ChartAnalysis) -> str:
    if analysis.liquidity_sweep:
        return "Liquidity Sweep"
    if analysis.equal_highs:
        return "Equal Highs"
    if analysis.equal_lows:
        return "Equal Lows"
    if "Above" in analysis.liquidity:
        return "Buy Side Liquidity"
    if "Below" in analysis.liquidity:
        return "Sell Side Liquidity"
    return "None Detected"


def _map_order_block(analysis: ChartAnalysis) -> str:
    if analysis.bullish_order_block:
        return "Bullish Order Block"
    if analysis.bearish_order_block:
        return "Bearish Order Block"
    return "None Detected"


def _map_fvg(analysis: ChartAnalysis) -> str:
    if not analysis.fair_value_gap:
        return "None Detected"
    if analysis.fvg_type == "Bullish FVG":
        return "Bullish FVG"
    if analysis.fvg_type == "Bearish FVG":
        return "Bearish FVG"
    return "Bullish FVG"


def _map_premium(analysis: ChartAnalysis) -> str:
    if analysis.premium == "Yes":
        return "Premium"
    if analysis.discount == "Yes":
        return "Discount"
    return "Equilibrium"


def _map_supply_demand(analysis: ChartAnalysis) -> str:
    if analysis.demand_zone and not analysis.supply_zone:
        return "Demand"
    if analysis.supply_zone and not analysis.demand_zone:
        return "Supply"
    return "Balanced"


def _summary(tf: str, analysis: ChartAnalysis) -> str:
    if analysis.status != "ok":
        return analysis.error or "Image Quality Too Low"
    return (
        f"{tf}: trend {analysis.trend} | structure {analysis.market_structure} | "
        f"BOS={'yes' if analysis.bos else 'no'} | CHOCH={'yes' if analysis.choch else 'no'} | "
        f"liquidity {analysis.liquidity} | conf {analysis.confidence:.0f}%"
    )


class AnalysisService:
    def __init__(self, brain: AIBrain | None = None) -> None:
        self.brain = brain or AIBrain()

    def analyze(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        persist: bool = True,
    ) -> AnalysisResult:
        decision = self.decide(
            pair=pair,
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            persist=persist,
        )
        return self.to_analysis_result(decision)

    def decide(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        persist: bool = True,
    ) -> TradeDecision:
        from core.analysis_jobs import AnalysisJobStore

        jobs = AnalysisJobStore()
        job_id = jobs.create(
            pair=pair,
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
        )
        jobs.mark_running(job_id)
        try:
            decision = self.brain.recommend(
                pair=pair,
                chart_4h=chart_4h,
                chart_1h=chart_1h,
                chart_15m=chart_15m,
                persist=persist,
            )
            jobs.mark_done(
                job_id,
                trade_id=decision.trade_id or "",
                payload={"bias": decision.overall_bias, "confidence": decision.confidence},
            )
            return decision
        except Exception as exc:
            jobs.mark_failed(job_id, str(exc))
            raise

    def to_analysis_result(self, decision: TradeDecision) -> AnalysisResult:
        a4 = decision.analysis_4h
        a1 = decision.analysis_1h
        a15 = decision.analysis_15m

        reasons = list(decision.reasons)
        if decision.warnings:
            reasons.extend([f"Warning: {w}" for w in decision.warnings])
        if decision.trade_id:
            reasons.append(f"Trade ID: {decision.trade_id}")

        return AnalysisResult(
            pair=decision.pair,
            bias=decision.overall_bias,
            confidence=decision.confidence,
            analysis4h={
                "trend": _map_trend(a4.trend),
                "marketStructure": _map_structure(a4),
                "liquidity": _map_liquidity(a4),
                "orderBlock": _map_order_block(a4),
                "fvg": _map_fvg(a4),
                "premiumDiscount": _map_premium(a4),
                "supplyDemand": _map_supply_demand(a4),
                "summary": _summary("4H", a4),
            },
            analysis1h={
                "trend": _map_trend(a1.trend),
                "liquidity": _map_liquidity(a1),
                "orderBlock": _map_order_block(a1),
                "fvg": _map_fvg(a1),
                "summary": _summary("1H", a1),
            },
            analysis15m={
                "entry": decision.entry,
                "stopLoss": decision.stop_loss,
                "takeProfit": decision.take_profit,
                "riskReward": decision.risk_reward,
                "reasons": reasons or ["No trade reasons produced."],
                "summary": (
                    f"Bias {decision.overall_bias} | "
                    f"Target liquidity: {decision.target_liquidity} | "
                    f"Status: {decision.status}"
                ),
            },
            finalDecision=decision.explanation,
            generatedAt=decision.generated_at or utc_now_iso(),
            warnings=decision.warnings,
            explanation=decision.explanation,
            targetLiquidity=decision.target_liquidity,
            tradeId=decision.trade_id,
            status=decision.status,
        )
