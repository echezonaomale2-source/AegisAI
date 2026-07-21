"""
AI Brain — central decision coordinator.

Never analyzes raw images. Never detects market structures.
Receives validated engine outputs and produces the final recommendation.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from brain.completeness import CompletenessChecker
from brain.conflicts import ConflictDetector
from brain.historical import HistoricalReasoner
from brain.models import (
    BrainRecommendation,
    EngineBundle,
    ReasonTrace,
    TradeBias,
)
from brain.self_check import BrainSelfChecker
from brain.trace_store import ReasonTraceStore
from cognitive.models.decision import CognitiveDecision
from cognitive.models.evidence import Evidence
from cognitive.models.market import MarketModel
from cognitive.models.reasoning import ReasoningReport
from cognitive.pipeline import CognitivePipeline
from core.logging_setup import get_logger
from evaluation.engine import EvaluationEngine
from knowledge.engine import KnowledgeEngine
from knowledge.versioning import CURRENT_VERSION
from memory.memory_service import MemoryService
from models.decision_schemas import TradeDecision
from research.orchestrator import ResearchOrchestrator
from storage.trade_store import TradeStore
from verification.discrepancy import DiscrepancyReporter
from verification.engine import VerificationEngine
from verification.models import VerificationSummary
from verification.provider import MarketDataProvider, NullMarketDataProvider

log = get_logger("brain")


class AIBrain:
    """
    Single entry point for trading recommendations.

    Orchestrates engines; does not duplicate their responsibilities.
    Deterministic given the same validated inputs.
    Prefers NO TRADE over low-quality recommendations.
    """

    def __init__(
        self,
        pipeline: CognitivePipeline | None = None,
        memory: MemoryService | None = None,
        research: ResearchOrchestrator | None = None,
        evaluation: EvaluationEngine | None = None,
        trade_store: TradeStore | None = None,
        market_provider: MarketDataProvider | None = None,
        verification: VerificationEngine | None = None,
    ) -> None:
        self.pipeline = pipeline or CognitivePipeline()
        self.memory = memory or MemoryService()
        self.research = research or ResearchOrchestrator()
        self.evaluation = evaluation or EvaluationEngine()
        self.trade_store = trade_store or TradeStore()
        self.completeness = CompletenessChecker()
        self.conflicts = ConflictDetector()
        self.historical = HistoricalReasoner(self.memory)
        self.self_check = BrainSelfChecker()
        self.traces = ReasonTraceStore()
        self.knowledge = KnowledgeEngine()
        # Phase 11 — optional; Null provider keeps screenshot-only by default
        self.verification = verification or VerificationEngine(
            provider=market_provider or NullMarketDataProvider(),
            reporter=DiscrepancyReporter(),
        )

    def recommend(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        persist: bool = True,
    ) -> TradeDecision:
        """
        Coordinate engines → BrainRecommendation → TradeDecision.

        Charts are passed only to Vision/Cognitive pipeline; the Brain
        itself reasons solely over validated outputs.
        """
        # 1. Gather validated engine outputs (orchestration only)
        markets, report, cognitive = self.pipeline.reason_multi(
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            pair=pair,
        )
        # Build provisional TradeDecision from cognitive (chart analysis — not Brain invention)
        provisional = self.pipeline._to_trade_decision(cognitive, markets, report)  # noqa: SLF001
        provisional = self.memory.apply_memory_to_decision(provisional)

        # Collect evidence maps from process_timeframe re-run is expensive —
        # reconstruct evidence summaries from reasoning report.
        evidence_by_tf = {
            "4H": {"buy": report.buy_evidence_score, "sell": report.sell_evidence_score},
            "1H": {},
            "15M": {},
        }
        # Prefer snapshot if present
        if report.evidence_snapshot:
            evidence_by_tf["aggregate"] = {
                "buy_weight": report.evidence_snapshot.buy_weight,
                "sell_weight": report.evidence_snapshot.sell_weight,
                "neutral_weight": report.evidence_snapshot.neutral_weight,
            }

        bundle = self._build_bundle(
            markets=markets,
            report=report,
            cognitive=cognitive,
            provisional=provisional,
        )

        trace = ReasonTrace(trace_id=str(uuid.uuid4()))
        trace.add("Vision Engine", "provided chart summaries", f"TFs={list(markets.keys())}")
        trace.add("Knowledge Engine", "validated concepts", f"version={CURRENT_VERSION}")
        for concept in bundle.validated_concepts[:8]:
            trace.add("Knowledge Engine", "validated", concept)
        trace.add(
            "Evidence Engine",
            "scored evidence",
            f"BUY {report.buy_evidence_score:.0f} / SELL {report.sell_evidence_score:.0f}",
        )
        for item in report.supporting[:5]:
            trace.add("Evidence Engine", "support", item.rationale or item.name)
        trace.add(
            "Reasoning Engine",
            "combined evidence",
            f"conclusion={report.conclusion} conf={report.confidence:.0f}%",
        )
        if cognitive.risk:
            trace.add(
                "Risk Engine",
                "assessed plan",
                f"valid={cognitive.risk.valid} RR={cognitive.risk.risk_reward} grade={cognitive.risk.risk_grade}",
            )

        # 2. Completeness
        completeness = self.completeness.check(bundle)
        trace.add(
            "Brain",
            "completeness check",
            f"complete={completeness.complete} missing={completeness.missing_critical}",
        )

        # 3. Conflicts
        conflicts = self.conflicts.detect(bundle)
        trace.add(
            "Brain",
            "conflict detection",
            f"severity={conflicts.severity} htf_disagreement={conflicts.htf_disagreement}",
        )

        # 4–5. Historical memory
        historical = self.historical.evaluate(provisional)
        trace.add(
            "Memory Engine",
            "historical support",
            f"{historical.historical_support} similar={historical.previous_similar_analyses} "
            f"{historical.wins}W/{historical.losses}L influence={historical.influence_on_confidence:+.1f}",
        )

        # 5b. Optional market-data verification (never required)
        verification = self.verification.verify_markets(
            markets,
            pair=provisional.pair,
            primary_tf="4H",
            persist=False,
        )
        bundle = bundle.model_copy(
            update={"market_verification": verification.model_dump(mode="json")}
        )
        trace.add(
            "Verification Engine",
            verification.status,
            f"match={verification.match_score:.0f} influence={verification.influence_on_confidence:+.1f}",
        )

        # 6. Confidence (chart + historical + optional verification — never override direction)
        confidence = (
            float(provisional.confidence)
            + historical.influence_on_confidence
            + verification.influence_on_confidence
        )
        confidence = max(0.0, min(100.0, confidence))
        candidate: TradeBias = provisional.overall_bias  # type: ignore[assignment]
        trace.add("Confidence Engine", "evaluated confidence", f"{confidence:.1f}%")

        # 7. Risk already in cognitive — Brain only gates
        if cognitive.risk and provisional.overall_bias in {"BUY", "SELL"} and not cognitive.risk.valid:
            candidate = "NO TRADE"
            trace.add("Risk Engine", "rejected plan", "invalid RR/geometry → NO TRADE")

        # Critical missing / poor quality / HTF disagreement → NO TRADE
        if completeness.missing_critical or completeness.poor_image_quality:
            candidate = "NO TRADE"
            confidence = min(confidence, 40.0)
            trace.add("Brain", "forced NO TRADE", "incomplete or poor-quality inputs")
        if conflicts.htf_disagreement and provisional.overall_bias in {"BUY", "SELL"}:
            candidate = "NO TRADE"
            trace.add("Brain", "forced NO TRADE", "higher timeframes disagree")

        # 8. Self-check
        check = self.self_check.check(
            bundle,
            completeness=completeness,
            conflicts=conflicts,
            historical=historical,
            confidence=confidence,
            candidate=candidate,
        )
        trace.add("Brain", "self-check", f"passed={check.passed} prefer_no_trade={check.prefer_no_trade}")
        if check.prefer_no_trade and candidate in {"BUY", "SELL"}:
            candidate = "NO TRADE"
            trace.add("Brain", "forced NO TRADE", "self-check prefers safer NO TRADE")

        if candidate in {"BUY", "SELL"} and confidence < 70:
            candidate = "NO TRADE"
            trace.add("Brain", "forced NO TRADE", "confidence below 70%")

        # Build recommendation
        if candidate == "NO TRADE":
            entry = stop = take = rr = "—"
            grade = "F"
        else:
            entry = provisional.entry
            stop = provisional.stop_loss
            take = provisional.take_profit
            rr = provisional.risk_reward
            grade = cognitive.trade_grade

        supporting = [i.rationale or i.name for i in report.supporting[:8]]
        conflicting = list(conflicts.conflicts) + [
            i.rationale or i.name for i in report.conflicting[:5]
        ]

        summary = (
            f"{candidate} on {provisional.pair} | "
            f"BUY evidence {report.buy_evidence_score:.0f} vs SELL {report.sell_evidence_score:.0f} | "
            f"historical {historical.historical_support}"
        )
        explanation = self._explain(
            candidate=candidate,
            provisional=provisional,
            report=report,
            historical=historical,
            completeness=completeness,
            conflicts=conflicts,
            check=check,
            confidence=confidence,
            verification=verification,
        )

        warnings = list(provisional.warnings) + list(check.warnings) + list(completeness.notes)
        warnings.extend(verification.warnings)
        if completeness.request_better_screenshot:
            warnings.append("Please upload a clearer screenshot for a reliable analysis.")
        warnings.append(f"Knowledge version: {CURRENT_VERSION}")

        # Deterministic hash from validated inputs (not random)
        det_payload = {
            "pair": provisional.pair,
            "candidate": candidate,
            "confidence": round(confidence, 1),
            "buy": report.buy_evidence_score,
            "sell": report.sell_evidence_score,
            "conclusion": report.conclusion,
            "htf_conflict": conflicts.htf_disagreement,
            "missing": completeness.missing_critical,
            "hist": historical.historical_support,
            "hist_inf": historical.influence_on_confidence,
            "verify_status": verification.status,
            "verify_inf": verification.influence_on_confidence,
        }
        det_hash = hashlib.sha256(
            json.dumps(det_payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        trace.deterministic_hash = det_hash
        trace.final_action = f"Brain approved {candidate}"
        trace.add("Brain", f"approved {candidate}", f"hash={det_hash}")

        recommendation = BrainRecommendation(
            pair=provisional.pair,
            timeframes=provisional.timeframes,
            summary=summary,
            recommendation=candidate,
            entry=entry,
            stop_loss=stop,
            take_profit=take,
            risk_reward=rr,
            confidence=round(confidence, 1),
            trade_grade=grade,  # type: ignore[arg-type]
            supporting_evidence=supporting,
            conflicting_evidence=conflicting,
            historical_support=historical,
            warnings=list(dict.fromkeys(warnings)),
            explanation=explanation,
            completeness=completeness,
            conflicts=conflicts,
            self_check=check,
            reason_trace=trace,
            request_better_screenshot=completeness.request_better_screenshot,
            verification=verification,
        )
        self._last_recommendation = recommendation

        # Map to TradeDecision for API / persistence compatibility
        decision = provisional.model_copy(
            update={
                "overall_bias": candidate,
                "entry": entry,
                "stop_loss": stop,
                "take_profit": take,
                "risk_reward": rr,
                "confidence": round(confidence, 1),
                "explanation": explanation,
                "reasons": supporting + [f"Trace: {det_hash}"],
                "warnings": recommendation.warnings,
            }
        )

        # Research calibration gate (non-duplicative final soft pass)
        decision = self.research.apply_pre_decision_gates(decision)
        # If research forces NO TRADE, align recommendation
        if decision.overall_bias == "NO TRADE" and candidate != "NO TRADE":
            trace.add("Research/Self-check", "forced NO TRADE", "pre-decision gates")
            candidate = "NO TRADE"
            decision = decision.model_copy(
                update={
                    "entry": "—",
                    "stop_loss": "—",
                    "take_profit": "—",
                    "risk_reward": "—",
                    "explanation": recommendation.explanation
                    + " Final gate enforced NO TRADE.",
                }
            )
            recommendation = recommendation.model_copy(
                update={"recommendation": "NO TRADE", "entry": "—", "stop_loss": "—", "take_profit": "—", "risk_reward": "—"}
            )
            trace.final_action = "Brain approved NO TRADE"

        if persist:
            decision = self.trade_store.save(
                decision,
                chart_4h=chart_4h,
                chart_1h=chart_1h,
                chart_15m=chart_15m,
            )
            trade_dir = self.trade_store.root / (decision.trade_id or "")
            self.memory.remember_decision(
                decision,
                chart_4h=trade_dir / next(trade_dir.glob("chart_4h.*")),
                chart_1h=trade_dir / next(trade_dir.glob("chart_1h.*")),
                chart_15m=trade_dir / next(trade_dir.glob("chart_15m.*")),
            )
            self.traces.save(trace, trade_id=decision.trade_id)
            self.verification.reporter.save(verification, trade_id=decision.trade_id)

        self.evaluation.record_decision(
            decision,
            validated_concepts=bundle.validated_concepts,
            evidence_summary={
                "buy_score": report.buy_evidence_score,
                "sell_score": report.sell_evidence_score,
                "neutral_score": report.neutral_score,
            },
            reasoning_summary={
                "conclusion": report.conclusion,
                "trace": det_hash,
                "brain": trace.final_action,
            },
            input_summary={"pair": pair, "persist": persist, "brain": True},
        )

        log.info(
            "brain decision=%s conf=%.1f hash=%s pair=%s",
            decision.overall_bias,
            decision.confidence,
            det_hash,
            decision.pair,
        )
        return decision

    def decide_from_bundle(
        self,
        bundle: EngineBundle,
        *,
        provisional: TradeDecision,
        report: ReasoningReport,
        cognitive: CognitiveDecision,
        verification: VerificationSummary | None = None,
    ) -> BrainRecommendation:
        """
        Pure Brain decision over already-validated inputs (unit-testable, deterministic).
        Does not call Vision or touch raw images.
        """
        trace = ReasonTrace(trace_id=str(uuid.uuid4()))
        trace.add("Brain", "received validated bundle", f"pair={bundle.pair}")
        for concept in bundle.validated_concepts[:8]:
            trace.add("Knowledge Engine", "validated", concept)
        trace.add(
            "Evidence Engine",
            "scored evidence",
            f"BUY {report.buy_evidence_score:.0f} / SELL {report.sell_evidence_score:.0f}",
        )
        trace.add("Reasoning Engine", "combined", f"conclusion={report.conclusion}")

        completeness = self.completeness.check(bundle)
        conflicts = self.conflicts.detect(bundle)
        historical = self.historical.evaluate(provisional)

        if verification is None:
            vs = bundle.vision_summaries.get("4H") or bundle.vision_summaries.get("1H") or {}
            verification = self.verification.verify_from_bundle_vision(
                pair=bundle.pair,
                timeframe="4H",
                vision_summary=vs if isinstance(vs, dict) else {},
            )
        trace.add(
            "Verification Engine",
            verification.status,
            f"match={verification.match_score:.0f} influence={verification.influence_on_confidence:+.1f}",
        )

        confidence = (
            float(provisional.confidence)
            + historical.influence_on_confidence
            + verification.influence_on_confidence
        )
        confidence = max(0.0, min(100.0, confidence))
        candidate: TradeBias = provisional.overall_bias  # type: ignore[assignment]

        if cognitive.risk and provisional.overall_bias in {"BUY", "SELL"} and not cognitive.risk.valid:
            candidate = "NO TRADE"
        if completeness.missing_critical or completeness.poor_image_quality:
            candidate = "NO TRADE"
            confidence = min(confidence, 40.0)
        if conflicts.htf_disagreement and provisional.overall_bias in {"BUY", "SELL"}:
            candidate = "NO TRADE"

        check = self.self_check.check(
            bundle,
            completeness=completeness,
            conflicts=conflicts,
            historical=historical,
            confidence=confidence,
            candidate=candidate,
        )
        if check.prefer_no_trade and candidate in {"BUY", "SELL"}:
            candidate = "NO TRADE"
        if candidate in {"BUY", "SELL"} and confidence < 70:
            candidate = "NO TRADE"

        if candidate == "NO TRADE":
            entry = stop = take = rr = "—"
            grade: str = "F"
        else:
            entry, stop, take, rr = (
                provisional.entry,
                provisional.stop_loss,
                provisional.take_profit,
                provisional.risk_reward,
            )
            grade = cognitive.trade_grade

        det_payload = {
            "pair": provisional.pair,
            "candidate": candidate,
            "confidence": round(confidence, 1),
            "buy": report.buy_evidence_score,
            "sell": report.sell_evidence_score,
            "htf_conflict": conflicts.htf_disagreement,
            "missing": completeness.missing_critical,
            "hist_inf": historical.influence_on_confidence,
            "verify_status": verification.status,
            "verify_inf": verification.influence_on_confidence,
        }
        det_hash = hashlib.sha256(
            json.dumps(det_payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        trace.deterministic_hash = det_hash
        trace.final_action = f"Brain approved {candidate}"

        supporting = [i.rationale or i.name for i in report.supporting[:8]]
        conflicting = list(conflicts.conflicts)

        rec = BrainRecommendation(
            pair=provisional.pair,
            timeframes=provisional.timeframes,
            summary=f"{candidate} | hist={historical.historical_support} | verify={verification.status}",
            recommendation=candidate,
            entry=entry,
            stop_loss=stop,
            take_profit=take,
            risk_reward=rr,
            confidence=round(confidence, 1),
            trade_grade=grade,  # type: ignore[arg-type]
            supporting_evidence=supporting,
            conflicting_evidence=conflicting,
            historical_support=historical,
            warnings=list(
                dict.fromkeys(
                    list(check.warnings) + list(completeness.notes) + list(verification.warnings)
                )
            ),
            explanation=self._explain(
                candidate=candidate,
                provisional=provisional,
                report=report,
                historical=historical,
                completeness=completeness,
                conflicts=conflicts,
                check=check,
                confidence=confidence,
                verification=verification,
            ),
            completeness=completeness,
            conflicts=conflicts,
            self_check=check,
            reason_trace=trace,
            request_better_screenshot=completeness.request_better_screenshot,
            verification=verification,
        )
        self._last_recommendation = rec
        return rec

    def recommend_detailed(
        self,
        *,
        pair: str,
        chart_4h: Path,
        chart_1h: Path,
        chart_15m: Path,
        persist: bool = False,
    ) -> tuple[TradeDecision, BrainRecommendation]:
        """Return TradeDecision plus full BrainRecommendation (for API / tests)."""
        # Run core path without double-persist: recommend handles persist flag.
        decision = self.recommend(
            pair=pair,
            chart_4h=chart_4h,
            chart_1h=chart_1h,
            chart_15m=chart_15m,
            persist=persist,
        )
        # Reconstruct a lightweight BrainRecommendation from decision + last trace file if needed.
        # For API, re-run gather is expensive — store last recommendation on instance.
        rec = getattr(self, "_last_recommendation", None)
        if rec is None:
            rec = BrainRecommendation(
                pair=decision.pair,
                timeframes=decision.timeframes,
                summary=decision.explanation[:200],
                recommendation=decision.overall_bias,  # type: ignore[arg-type]
                entry=decision.entry,
                stop_loss=decision.stop_loss,
                take_profit=decision.take_profit,
                risk_reward=decision.risk_reward,
                confidence=decision.confidence,
                warnings=list(decision.warnings),
                explanation=decision.explanation,
                supporting_evidence=list(decision.reasons),
            )
        return decision, rec

    def _build_bundle(
        self,
        *,
        markets: dict[str, MarketModel],
        report: ReasoningReport,
        cognitive: CognitiveDecision,
        provisional: TradeDecision,
    ) -> EngineBundle:
        vision_summaries = {}
        validated: list[str] = []
        for tf, market in markets.items():
            vision_summaries[tf] = {
                "status": market.status,
                "quality": market.image_quality_score,
                "trend": market.trend.direction,
                "structure": market.structure_label,
                "bos": market.bos,
                "choch": market.choch,
                "pair": market.pair,
                "candle_count": len(market.candles),
                "candle_closes": [float(c.close) for c in market.candles[-20:]],
                "swing_highs": [
                    float(s.price) for s in market.swing_points if s.kind == "high"
                ][-5:],
                "swing_lows": [
                    float(s.price) for s in market.swing_points if s.kind == "low"
                ][-5:],
            }
            # Knowledge Engine is SSOT — Vision candidates only become validated after rules pass
            ctx = self.knowledge.build_context_from_market(market)
            candidates: list[str] = []
            if market.bos:
                candidates.append("bos")
            if market.choch:
                candidates.append("choch")
            if any(o.side == "bullish" for o in market.order_blocks):
                candidates.append("bullish_order_block")
            if any(o.side == "bearish" for o in market.order_blocks):
                candidates.append("bearish_order_block")
            if any(g.side == "bullish" for g in market.fair_value_gaps):
                candidates.append("bullish_fvg")
            if any(g.side == "bearish" for g in market.fair_value_gaps):
                candidates.append("bearish_fvg")
            if any(z.kind == "sweep" or z.swept for z in market.liquidity):
                candidates.append("liquidity_sweep")
            has_internal = any(z.kind == "internal" for z in market.liquidity)
            has_external = any(z.kind == "external" for z in market.liquidity)
            if has_internal:
                candidates.append("internal_liquidity")
            if has_external:
                candidates.append("external_liquidity")
            if market.liquidity and not has_internal and not has_external:
                candidates.append("liquidity")
            if market.trend.direction == "Bullish":
                candidates.append("bullish_trend")
            elif market.trend.direction == "Bearish":
                candidates.append("bearish_trend")
            elif market.trend.direction == "Range":
                candidates.append("range")

            for concept_id in candidates:
                result = self.knowledge.validate_concept(concept_id, ctx)
                if result.status == "valid":
                    validated.append(f"{tf}:{concept_id}")

        risk = {}
        if cognitive.risk:
            risk = cognitive.risk.model_dump(mode="json")

        return EngineBundle(
            pair=provisional.pair,
            timeframes=provisional.timeframes,
            vision_summaries=vision_summaries,
            knowledge_version=CURRENT_VERSION,
            validated_concepts=validated,
            feature_summaries={tf: {"candles": len(m.candles)} for tf, m in markets.items()},
            evidence_by_tf={
                "4H": {"buy": report.buy_evidence_score, "sell": report.sell_evidence_score},
            },
            reasoning=report.model_dump(mode="json"),
            risk=risk,
            memory={},
            learning={},
            confidence={"provisional": provisional.confidence, "scorecard": provisional.confidence_scorecard.model_dump()},
            provisional_bias=provisional.overall_bias,  # type: ignore[arg-type]
            provisional_confidence=provisional.confidence,
            provisional_entry=provisional.entry,
            provisional_stop=provisional.stop_loss,
            provisional_take=provisional.take_profit,
            provisional_rr=provisional.risk_reward,
            provisional_grade=cognitive.trade_grade,  # type: ignore[arg-type]
            provisional_explanation=provisional.explanation,
        )

    def _explain(
        self,
        *,
        candidate: str,
        provisional: TradeDecision,
        report: ReasoningReport,
        historical,
        completeness,
        conflicts,
        check,
        confidence: float,
        verification: VerificationSummary | None = None,
    ) -> str:
        parts = [
            f"AI Brain recommendation: {candidate} at {confidence:.0f}% confidence.",
            f"Chart evidence — BUY {report.buy_evidence_score:.0f} / SELL {report.sell_evidence_score:.0f} / Neutral {report.neutral_score:.0f}.",
            f"Historical support: {historical.historical_support} "
            f"({historical.previous_similar_analyses} similar, {historical.wins}W/{historical.losses}L).",
        ]
        if verification is not None:
            if verification.screenshot_only:
                parts.append("Market verification: screenshots only (no live/historical OHLC applied).")
            else:
                parts.append(
                    f"Market verification: {verification.status} "
                    f"(match {verification.match_score:.0f}%, "
                    f"confidence influence {verification.influence_on_confidence:+.1f})."
                )
        if completeness.missing_critical:
            parts.append("Missing critical evidence: " + ", ".join(completeness.missing_critical))
        if conflicts.conflicts:
            parts.append("Conflicts: " + "; ".join(conflicts.conflicts[:3]))
        if check.prefer_no_trade:
            parts.append("Self-check preferred NO TRADE as the safer professional conclusion.")
        if candidate in {"BUY", "SELL"}:
            parts.append(
                f"Levels: entry {provisional.entry} | SL {provisional.stop_loss} | "
                f"TP {provisional.take_profit} | RR {provisional.risk_reward}."
            )
        parts.append("The Brain coordinates engines and does not invent missing structures.")
        return " ".join(parts)
