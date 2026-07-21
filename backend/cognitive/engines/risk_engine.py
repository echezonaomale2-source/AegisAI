"""Engine 7 — Risk Engine: trade quality, RR, nearby zones, risk grade."""

from __future__ import annotations

from cognitive.events import EVT_RISK_ASSESSED, EventBus
from cognitive.models.market import MarketModel
from cognitive.models.reasoning import ReasoningReport
from cognitive.models.risk import RiskAssessment
from core.adapters import chart_model_to_chart_analysis
from core.logging_setup import get_logger
from core.models.chart import ChartModel
from decision.risk_engine import RiskEngine as LegacyRiskEngine
from models.decision_schemas import TradeDirection

log = get_logger("cognitive.risk")


class CognitiveRiskEngine:
    """
    Evaluate trade quality from reasoning conclusion + market geometry.

    Wraps Phase 3 RiskEngine for entry/SL/TP, then grades risk holistically.
    """

    def __init__(self, bus: EventBus | None = None) -> None:
        self._legacy = LegacyRiskEngine()
        self._bus = bus

    def assess(
        self,
        report: ReasoningReport,
        markets: dict[str, MarketModel],
    ) -> RiskAssessment:
        direction: TradeDirection = report.conclusion  # type: ignore[assignment]
        if direction == "NO TRADE":
            assessment = RiskAssessment(
                risk_grade="F",
                valid=False,
                notes=["No risk plan — decision is NO TRADE."],
            )
            if self._bus:
                self._bus.publish(EVT_RISK_ASSESSED, {"grade": "F", "valid": False})
            return assessment

        h4 = self._to_analysis(markets.get("4H"))
        h1 = self._to_analysis(markets.get("1H"))
        m15 = self._to_analysis(markets.get("15M"))
        plan = self._legacy.build(direction=direction, h4=h4, h1=h1, m15=m15)

        if plan.trade_direction == "NO TRADE":
            assessment = RiskAssessment(
                entry=plan.entry,
                stop_loss=plan.stop_loss,
                take_profit=plan.take_profit,
                risk_reward=plan.risk_reward,
                risk_grade="F",
                valid=False,
                notes=list(plan.notes),
            )
            if self._bus:
                self._bus.publish(EVT_RISK_ASSESSED, {"grade": "F", "valid": False})
            return assessment

        rr = self._parse_rr(plan.risk_reward)
        m15_market = markets.get("15M") or markets.get("1H")
        nearby_supply = bool(m15_market and m15_market.supply)
        nearby_demand = bool(m15_market and m15_market.demand)
        nearby_liq = "Unknown"
        if m15_market and m15_market.liquidity:
            top = max(m15_market.liquidity, key=lambda z: z.confidence)
            nearby_liq = top.label or top.kind

        session_risk = self._session_risk(m15_market)
        conf_adj = 0.0
        notes = list(plan.notes)

        if rr is not None and rr < 1.5:
            conf_adj -= 15.0
            notes.append(f"RR {rr:.2f} below 1.5 — confidence penalized.")
        elif rr is not None and rr >= 2.0:
            conf_adj += 5.0
            notes.append(f"Favorable RR {rr:.2f}.")

        if direction == "BUY" and nearby_supply:
            conf_adj -= 8.0
            notes.append("Nearby supply / resistance above entry.")
        if direction == "SELL" and nearby_demand:
            conf_adj -= 8.0
            notes.append("Nearby demand / support below entry.")

        if session_risk == "High":
            conf_adj -= 5.0
            notes.append("Elevated session risk.")

        grade = self._grade(rr, conf_adj, report.confidence)
        dist_stop = dist_target = None
        try:
            entry_f = float(plan.entry)
            sl_f = float(plan.stop_loss)
            tp_f = float(plan.take_profit)
            dist_stop = abs(entry_f - sl_f)
            dist_target = abs(tp_f - entry_f)
        except (TypeError, ValueError):
            pass

        assessment = RiskAssessment(
            entry=plan.entry,
            stop_loss=plan.stop_loss,
            take_profit=plan.take_profit,
            risk_reward=plan.risk_reward,
            distance_to_stop=dist_stop,
            distance_to_target=dist_target,
            rr_numeric=rr,
            nearby_liquidity=nearby_liq,
            nearby_supply=nearby_supply,
            nearby_demand=nearby_demand,
            session_risk=session_risk,
            confidence_adjustment=conf_adj,
            risk_grade=grade,
            notes=notes,
            valid=rr is not None and rr >= 1.5,
        )
        log.info(
            "risk grade=%s rr=%s valid=%s adj=%.1f",
            grade,
            plan.risk_reward,
            assessment.valid,
            conf_adj,
        )
        if self._bus:
            self._bus.publish(
                EVT_RISK_ASSESSED,
                {"grade": grade, "valid": assessment.valid, "rr": plan.risk_reward},
            )
        return assessment

    def _to_analysis(self, market: MarketModel | None):
        from models.chart_schemas import ChartAnalysis

        if market is None or not market.is_usable:
            return ChartAnalysis(status="error", error="Missing market")
        chart = market.source_chart or ChartModel(
            status="ok",
            pair=market.pair,
            timeframe=market.timeframe,
            candles=list(market.candles),
            trend=market.trend,
            bos=market.bos,
            choch=market.choch,
            liquidity_zones=list(market.liquidity),
            order_blocks=list(market.order_blocks),
            fair_value_gaps=list(market.fair_value_gaps),
            supply_zones=list(market.supply),
            demand_zones=list(market.demand),
            premium=market.premium,
            discount=market.discount,
        )
        return chart_model_to_chart_analysis(chart)

    def _parse_rr(self, rr: str) -> float | None:
        if not rr or rr == "—":
            return None
        text = rr.lower().replace(" ", "")
        if ":" in text:
            try:
                a, b = text.split(":", 1)
                risk = float(a)
                reward = float(b)
                if risk <= 0:
                    return None
                return reward / risk
            except ValueError:
                return None
        try:
            return float(text)
        except ValueError:
            return None

    def _session_risk(self, market: MarketModel | None) -> str:
        if market is None:
            return "Unknown"
        labels = (market.metadata or {}).get("session_labels") or []
        joined = " ".join(str(x).lower() for x in labels)
        if any(k in joined for k in ("news", "fomc", "nfp", "cpi")):
            return "High"
        if any(k in joined for k in ("london", "new york", "ny", "overlap")):
            return "Medium"
        if labels:
            return "Low"
        return "Unknown"

    def _grade(self, rr: float | None, conf_adj: float, confidence: float) -> str:
        score = confidence + conf_adj
        if rr is not None:
            score += min(15.0, (rr - 1.5) * 8.0)
        if score >= 85 and rr is not None and rr >= 2.0:
            return "A"
        if score >= 75 and rr is not None and rr >= 1.5:
            return "B"
        if score >= 65 and rr is not None and rr >= 1.5:
            return "C"
        if score >= 50:
            return "D"
        return "F"
