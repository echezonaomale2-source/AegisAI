"""
Cognitive master pipeline (Phase 6).

User Uploads → Vision → Chart Reconstruction → Feature Extraction
→ Evidence → Reasoning → Decision → Risk → Memory → Learning
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from cognitive.container import CognitiveContainer, get_cognitive_container
from cognitive.models.decision import CognitiveDecision
from cognitive.models.evidence import Evidence
from cognitive.models.market import MarketModel
from cognitive.models.reasoning import ReasoningReport
from core.adapters import chart_model_to_chart_analysis
from core.logging_setup import get_logger
from knowledge.engine import KnowledgeEngine
from knowledge.versioning import CURRENT_VERSION
from models.chart_schemas import ChartAnalysis, MultiChartAnalysis
from models.decision_schemas import ConfidenceScorecard, TradeDecision
from models.schemas import utc_now_iso
from vision.chart_parser import normalize_pair, normalize_timeframe

log = get_logger("cognitive.pipeline")


class CognitivePipeline:
    def __init__(
        self,
        container: CognitiveContainer | None = None,
        knowledge: KnowledgeEngine | None = None,
    ) -> None:
        self.c = container or get_cognitive_container()
        self.knowledge = knowledge or KnowledgeEngine()

    def process_timeframe(
        self,
        path: Path | str,
        *,
        expected_timeframe: str,
        pair: str | None = None,
    ) -> tuple[MarketModel, Evidence]:
        chart = self.c.vision.process(
            path, expected_timeframe=expected_timeframe, pair=pair
        )
        market = self.c.reconstruction.rebuild(chart)
        features = self.c.features.extract(market)
        # Phase 8: Knowledge Engine validates before Evidence consumes features.
        validated = self.knowledge.validate_features(features, market)
        weights = self.c.learning.current_weights()
        evidence = self.c.evidence.evaluate(
            validated,
            image_quality=market.image_quality_score or chart.image_quality_score,
            feature_weights=weights,
        )
        return market, evidence

    def reason_multi(
        self,
        *,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        pair: str = "Unknown",
        timeframe_htf: str = "4H",
        timeframe_mtf: str = "1H",
        timeframe_ltf: str = "15M",
        historical_bias: float = 0.0,
    ) -> tuple[dict[str, MarketModel], ReasoningReport, CognitiveDecision]:
        resolved_pair = normalize_pair(pair)
        htf = normalize_timeframe(timeframe_htf, default="4H")
        mtf = normalize_timeframe(timeframe_mtf, default="1H")
        ltf = normalize_timeframe(timeframe_ltf, default="15M")

        m4, e4 = self.process_timeframe(
            chart_4h, expected_timeframe=htf, pair=resolved_pair
        )
        m1, e1 = self.process_timeframe(
            chart_1h, expected_timeframe=mtf, pair=resolved_pair
        )
        m15, e15 = self.process_timeframe(
            chart_15m, expected_timeframe=ltf, pair=resolved_pair
        )

        # Slot keys remain HTF/MTF/LTF roles for downstream engines.
        markets = {"4H": m4, "1H": m1, "15M": m15}
        evidence_by_tf = {"4H": e4, "1H": e1, "15M": e15}

        report = self.c.reasoning.reason(
            evidence_by_tf,
            historical_bias=historical_bias,
            pair=resolved_pair,
        )
        risk = self.c.risk.assess(report, markets)
        decision = self.c.decision.decide(report, risk, pair=resolved_pair)
        self._last_timeframes = {"HTF": htf, "MTF": mtf, "LTF": ltf}
        return markets, report, decision

    def decide(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        timeframe_htf: str = "4H",
        timeframe_mtf: str = "1H",
        timeframe_ltf: str = "15M",
        persist: bool = True,
    ) -> TradeDecision:
        markets, report, cognitive = self.reason_multi(
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            pair=pair,
            timeframe_htf=timeframe_htf,
            timeframe_mtf=timeframe_mtf,
            timeframe_ltf=timeframe_ltf,
        )

        legacy = self._to_trade_decision(cognitive, markets, report)

        # Memory-adjusted confidence (Phase 4) — does not erase cognitive trail.
        legacy = self.c.memory.apply_memory_bias(legacy)
        legacy = legacy.model_copy(
            update={
                "warnings": list(legacy.warnings)
                + [f"Knowledge version: {self.knowledge.version}"],
            }
        )

        # If memory pushes confidence below threshold on a trade, flip to NO TRADE.
        if legacy.overall_bias in {"BUY", "SELL"} and legacy.confidence < 70:
            legacy = legacy.model_copy(
                update={
                    "overall_bias": "NO TRADE",
                    "entry": "—",
                    "stop_loss": "—",
                    "take_profit": "—",
                    "risk_reward": "—",
                    "warnings": list(legacy.warnings)
                    + ["Memory-adjusted confidence below 70% — NO TRADE."],
                    "explanation": legacy.explanation
                    + " Memory adjustment invalidated the trade.",
                }
            )

        if persist:
            cognitive = cognitive.model_copy(
                update={
                    "recommendation": legacy.overall_bias,
                    "confidence": legacy.confidence,
                    "entry": legacy.entry,
                    "stop_loss": legacy.stop_loss,
                    "take_profit": legacy.take_profit,
                    "risk_reward": legacy.risk_reward,
                    "warnings": list(legacy.warnings),
                }
            )
            legacy = self.c.memory.remember(
                cognitive,
                chart_4h=chart_4h,
                chart_1h=chart_1h,
                chart_15m=chart_15m,
                legacy_decision=legacy,
            )
            # Attach cognitive hash into warnings for audit
            if cognitive.reproducible_hash:
                legacy = legacy.model_copy(
                    update={
                        "warnings": list(legacy.warnings)
                        + [f"Cognitive hash: {cognitive.reproducible_hash}"],
                        "trade_id": legacy.trade_id,
                    }
                )

        log.info(
            "cognitive pipeline %s conf=%.1f grade=%s",
            legacy.overall_bias,
            legacy.confidence,
            cognitive.trade_grade,
        )
        return legacy

    def analyze_multi_legacy(
        self,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        *,
        pair: str = "Unknown",
        timeframe_htf: str = "4H",
        timeframe_mtf: str = "1H",
        timeframe_ltf: str = "15M",
    ) -> MultiChartAnalysis:
        markets, _, _ = self.reason_multi(
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            pair=pair,
            timeframe_htf=timeframe_htf,
            timeframe_mtf=timeframe_mtf,
            timeframe_ltf=timeframe_ltf,
        )
        a4 = self._market_to_analysis(markets["4H"])
        a1 = self._market_to_analysis(markets["1H"])
        a15 = self._market_to_analysis(markets["15M"])
        statuses = [a4.status, a1.status, a15.status]
        status = (
            "ok"
            if all(s == "ok" for s in statuses)
            else "error"
            if all(s == "error" for s in statuses)
            else "partial"
        )
        return MultiChartAnalysis(
            status=status,
            chart_4h=a4,
            chart_1h=a1,
            chart_15m=a15,
            notes=["Phase 6 cognitive pipeline — MarketModel based extraction."],
        )

    def _market_to_analysis(self, market: MarketModel) -> ChartAnalysis:
        if market.source_chart is not None:
            return chart_model_to_chart_analysis(market.source_chart)
        if not market.is_usable:
            return ChartAnalysis(
                status="error",
                error=market.error or "Image Quality Too Low",
                pair=market.pair,
                timeframe=market.timeframe,
            )
        from core.models.chart import ChartModel

        chart = ChartModel(
            status="ok",
            pair=market.pair,
            timeframe=market.timeframe,
            candles=list(market.candles),
            swing_points=list(market.swing_points),
            trend=market.trend,
            market_structure_label=market.structure_label,
            bos=market.bos,
            choch=market.choch,
            liquidity_zones=list(market.liquidity),
            order_blocks=list(market.order_blocks),
            fair_value_gaps=list(market.fair_value_gaps),
            supply_zones=list(market.supply),
            demand_zones=list(market.demand),
            premium=market.premium,
            discount=market.discount,
            image_quality_score=market.image_quality_score,
            reconstruction_confidence=market.reconstruction_confidence,
            notes=list(market.notes),
        )
        return chart_model_to_chart_analysis(chart)

    def _to_trade_decision(
        self,
        cognitive: CognitiveDecision,
        markets: dict[str, MarketModel],
        report: ReasoningReport,
    ) -> TradeDecision:
        a4 = self._market_to_analysis(markets["4H"])
        a1 = self._market_to_analysis(markets["1H"])
        a15 = self._market_to_analysis(markets["15M"])

        scorecard = ConfidenceScorecard(
            htf_4h_alignment=report.buy_evidence_score
            if cognitive.recommendation == "BUY"
            else report.sell_evidence_score
            if cognitive.recommendation == "SELL"
            else max(report.buy_evidence_score, report.sell_evidence_score),
            mtf_1h_alignment=report.trace.get("margin", 0.0),
            ltf_15m_confirmation=report.confidence,
            liquidity=next(
                (i.confidence for i in report.supporting if "liquidity" in i.feature_type),
                40.0,
            ),
            order_block=next(
                (i.confidence for i in report.supporting if "order_block" in i.feature_type),
                40.0,
            ),
            fair_value_gap=next(
                (i.confidence for i in report.supporting if "fvg" in i.feature_type),
                40.0,
            ),
            market_structure=report.buy_evidence_score
            if report.conclusion == "BUY"
            else report.sell_evidence_score,
            overall=cognitive.confidence,
            weights={
                "buy_evidence": report.buy_evidence_score,
                "sell_evidence": report.sell_evidence_score,
                "neutral": report.neutral_score,
                **{k: float(v) for k, v in report.trace.items()},
            },
        )

        explanation = cognitive.explanation
        if cognitive.trade_grade:
            explanation = f"[Grade {cognitive.trade_grade}] {explanation}"
        if cognitive.reproducible_hash:
            explanation += f" (hash {cognitive.reproducible_hash})"

        return TradeDecision(
            pair=cognitive.pair,
            timeframes=getattr(
                self,
                "_last_timeframes",
                {"HTF": "4H", "MTF": "1H", "LTF": "15M"},
            ),
            analysis_4h=a4,
            analysis_1h=a1,
            analysis_15m=a15,
            overall_bias=cognitive.recommendation,
            entry=cognitive.entry,
            stop_loss=cognitive.stop_loss,
            take_profit=cognitive.take_profit,
            risk_reward=cognitive.risk_reward,
            target_liquidity=(
                cognitive.risk.nearby_liquidity if cognitive.risk else "None"
            ),
            confidence=cognitive.confidence,
            confidence_scorecard=scorecard,
            explanation=explanation,
            reasons=list(cognitive.reasons),
            warnings=list(cognitive.warnings),
            generated_at=utc_now_iso(),
        )
