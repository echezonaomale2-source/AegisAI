"""
VerificationEngine — compare screenshot reconstruction with optional OHLC data.

Never requires market data. Never fails the analysis when data is unavailable.
Does not detect structures itself — only compares validated visual fields to OHLC.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from core.logging_setup import get_logger
from verification.confidence import influence_from_match
from verification.discrepancy import DiscrepancyReporter
from verification.models import (
    ChartVisualSnapshot,
    Discrepancy,
    MarketDataSnapshot,
    VerificationSummary,
)
from verification.provider import MarketDataProvider, NullMarketDataProvider
from verification.visual import from_market_model, from_vision_summary

log = get_logger("verification")

# Relative tolerance for high/low price comparison (FX-friendly)
PRICE_TOL_PCT = 0.35
# Max age of screenshot vs market as_of before "image_too_old"
MAX_IMAGE_AGE_HOURS = 48.0
# Candle sequence correlation-ish: fraction of directional agreement
CANDLE_DIR_MIN_MATCH = 0.55


class VerificationEngine:
    """
    Optional market-data verification layer.

    Screenshot analysis is primary. OHLC verification adjusts confidence only.
    """

    def __init__(
        self,
        provider: MarketDataProvider | None = None,
        reporter: DiscrepancyReporter | None = None,
    ) -> None:
        self.provider: MarketDataProvider = provider or NullMarketDataProvider()
        self.reporter = reporter or DiscrepancyReporter()

    def verify_screenshot_only(self, *, pair: str = "Unknown", timeframe: str = "Unknown") -> VerificationSummary:
        """Explicit screenshot-only outcome (no provider call)."""
        summary = VerificationSummary(
            status="screenshot_only",
            provider_used=None,
            pair=pair,
            timeframe=timeframe,
            match_score=0.0,
            influence_on_confidence=0.0,
            significant_disagreement=False,
            screenshot_only=True,
            notes=["No market data supplied — screenshot analysis only."],
            verified_at=datetime.now(timezone.utc),
        )
        summary.warnings = self.reporter.warnings_for(summary)
        return summary

    def verify(
        self,
        visual: ChartVisualSnapshot,
        market: MarketDataSnapshot | None = None,
        *,
        persist: bool = False,
        trade_id: str | None = None,
    ) -> VerificationSummary:
        """
        Compare visual snapshot to market data.

        If market is None, attempts provider.fetch when available.
        On missing provider / network failure → screenshot_only or unavailable (never raises).
        """
        pair = visual.pair
        timeframe = visual.timeframe

        if market is None:
            market = self._safe_fetch(pair, timeframe)

        if market is None or not market.usable:
            status = "unavailable" if self.provider.available() else "screenshot_only"
            if self.provider.available() and market is None:
                # Provider claimed available but returned nothing
                status = "unavailable"
            summary = VerificationSummary(
                status=status,
                provider_used=getattr(self.provider, "name", None),
                pair=pair,
                timeframe=timeframe,
                screenshot_only=True,
                notes=[
                    "Market data unavailable — continuing with screenshot analysis."
                    if status == "unavailable"
                    else "Screenshot-only analysis (no market data provider)."
                ],
                discrepancies=(
                    [
                        Discrepancy(
                            kind="unable_to_verify",
                            severity="low",
                            message="Provider returned no usable OHLC candles.",
                        )
                    ]
                    if status == "unavailable"
                    else []
                ),
                verified_at=datetime.now(timezone.utc),
            )
            summary.influence_on_confidence = influence_from_match(
                status=summary.status,
                match_score=0.0,
                discrepancies=summary.discrepancies,
                significant=False,
            )
            summary.warnings = self.reporter.warnings_for(summary)
            if persist:
                self.reporter.save(summary, trade_id=trade_id)
            return summary

        discrepancies = self._compare(visual, market)
        significant = any(d.severity == "high" for d in discrepancies) or (
            sum(1 for d in discrepancies if d.severity in {"medium", "high"}) >= 2
        )
        match_score = self._match_score(discrepancies)
        if significant:
            status = "verified_conflict"
        elif discrepancies:
            status = "verified_partial"
        else:
            status = "verified_match"

        influence = influence_from_match(
            status=status,
            match_score=match_score,
            discrepancies=discrepancies,
            significant=significant,
        )

        summary = VerificationSummary(
            status=status,
            provider_used=market.provider_name or getattr(self.provider, "name", None),
            pair=pair,
            timeframe=timeframe,
            discrepancies=discrepancies,
            match_score=match_score,
            influence_on_confidence=influence,
            significant_disagreement=significant,
            screenshot_only=False,
            notes=[
                f"Compared screenshot vs {market.provider_name} OHLC "
                f"({len(market.candles)} candles)."
            ],
            verified_at=datetime.now(timezone.utc),
        )
        summary.warnings = self.reporter.warnings_for(summary)
        if persist:
            self.reporter.save(summary, trade_id=trade_id)
        log.info(
            "verification status=%s match=%.1f influence=%+.1f pair=%s tf=%s",
            status,
            match_score,
            influence,
            pair,
            timeframe,
        )
        return summary

    def verify_markets(
        self,
        markets: dict[str, Any] | Iterable[Any],
        *,
        pair: str,
        primary_tf: str = "4H",
        persist: bool = False,
        trade_id: str | None = None,
    ) -> VerificationSummary:
        """
        Verify using MarketModel map/list from CognitivePipeline.

        Uses primary timeframe (default 4H) for OHLC fetch comparison.
        """
        market_map: dict[str, Any] = {}
        if isinstance(markets, dict):
            market_map = markets
        else:
            for m in markets:
                tf = str(getattr(m, "timeframe", "") or "").upper()
                if tf:
                    market_map[tf] = m

        primary = (
            market_map.get(primary_tf)
            or market_map.get(primary_tf.upper())
            or next(iter(market_map.values()), None)
        )
        if primary is None:
            return self.verify_screenshot_only(pair=pair, timeframe=primary_tf)

        visual = from_market_model(primary)
        if visual.pair in {"Unknown", ""}:
            visual = visual.model_copy(update={"pair": pair})
        return self.verify(visual, persist=persist, trade_id=trade_id)

    def verify_from_bundle_vision(
        self,
        *,
        pair: str,
        timeframe: str,
        vision_summary: dict[str, Any],
        market: MarketDataSnapshot | None = None,
        persist: bool = False,
    ) -> VerificationSummary:
        visual = from_vision_summary(pair=pair, timeframe=timeframe, summary=vision_summary)
        return self.verify(visual, market, persist=persist)

    def _safe_fetch(self, pair: str, timeframe: str) -> MarketDataSnapshot | None:
        if not self.provider.available():
            return None
        try:
            return self.provider.fetch(pair, timeframe)
        except Exception as exc:  # noqa: BLE001 — never fail analysis
            log.warning("market data fetch failed: %s", exc)
            return None

    def _compare(
        self,
        visual: ChartVisualSnapshot,
        market: MarketDataSnapshot,
    ) -> list[Discrepancy]:
        out: list[Discrepancy] = []

        # Pair
        if (
            visual.pair
            and visual.pair.upper() not in {"UNKNOWN", ""}
            and market.pair.upper() not in {"UNKNOWN", ""}
            and visual.pair.upper() != market.pair.upper()
        ):
            out.append(
                Discrepancy(
                    kind="pair_mismatch",
                    severity="high",
                    message="Detected pair does not match market data pair.",
                    screenshot_value=visual.pair,
                    market_value=market.pair,
                )
            )

        # Timeframe
        v_tf = _norm_tf(visual.timeframe)
        m_tf = _norm_tf(market.timeframe)
        if v_tf and m_tf and v_tf != m_tf:
            out.append(
                Discrepancy(
                    kind="timeframe_mismatch",
                    severity="high",
                    message="Detected timeframe does not match market data timeframe.",
                    screenshot_value=visual.timeframe,
                    market_value=market.timeframe,
                )
            )

        # Trend from market closes
        m_trend = _trend_from_closes([c.close for c in market.candles])
        v_trend = _norm_trend(visual.trend)
        if v_trend not in {"Unknown", ""} and m_trend != "Unknown" and v_trend != m_trend:
            out.append(
                Discrepancy(
                    kind="trend_mismatch",
                    severity="high",
                    message="Screenshot trend disagrees with OHLC-derived trend.",
                    screenshot_value=visual.trend,
                    market_value=m_trend,
                )
            )

        # Recent highs / lows
        m_high = max(c.high for c in market.candles)
        m_low = min(c.low for c in market.candles)
        if visual.recent_high is not None and not _price_close(visual.recent_high, m_high):
            out.append(
                Discrepancy(
                    kind="high_mismatch",
                    severity="medium",
                    message="Recent high diverges from market OHLC high.",
                    screenshot_value=f"{visual.recent_high:.5f}",
                    market_value=f"{m_high:.5f}",
                )
            )
        if visual.recent_low is not None and not _price_close(visual.recent_low, m_low):
            out.append(
                Discrepancy(
                    kind="low_mismatch",
                    severity="medium",
                    message="Recent low diverges from market OHLC low.",
                    screenshot_value=f"{visual.recent_low:.5f}",
                    market_value=f"{m_low:.5f}",
                )
            )

        # Swing structure (HH/HL vs LH/LL heuristic from market)
        m_structure = _structure_from_closes([c.close for c in market.candles])
        v_structure = _norm_structure(visual.structure_label)
        if (
            v_structure not in {"Unknown", ""}
            and m_structure not in {"Unknown", ""}
            and not _structure_compatible(v_structure, m_structure)
        ):
            out.append(
                Discrepancy(
                    kind="swing_structure_mismatch",
                    severity="medium",
                    message="Swing structure label conflicts with OHLC swing pattern.",
                    screenshot_value=visual.structure_label,
                    market_value=m_structure,
                )
            )

        # Candle sequence (directional agreement on last N closes)
        if visual.candle_closes and len(market.candles) >= 3:
            seq_ok = _candle_sequence_agree(
                visual.candle_closes,
                [c.close for c in market.candles],
            )
            if not seq_ok:
                out.append(
                    Discrepancy(
                        kind="candle_sequence_mismatch",
                        severity="medium",
                        message="Approximate candle sequence disagrees with market closes.",
                    )
                )

        # Missing candles
        if visual.candle_count > 0 and len(market.candles) < max(3, visual.candle_count // 3):
            out.append(
                Discrepancy(
                    kind="missing_candles",
                    severity="low",
                    message="Market series has far fewer candles than the reconstructed chart.",
                    screenshot_value=str(visual.candle_count),
                    market_value=str(len(market.candles)),
                )
            )

        # Image too old
        if visual.captured_at and market.as_of:
            age_h = abs((market.as_of - visual.captured_at).total_seconds()) / 3600.0
            if age_h > MAX_IMAGE_AGE_HOURS:
                out.append(
                    Discrepancy(
                        kind="image_too_old",
                        severity="high",
                        message=f"Screenshot appears stale vs market data ({age_h:.1f}h gap).",
                        screenshot_value=visual.captured_at.isoformat(),
                        market_value=market.as_of.isoformat(),
                    )
                )

        return out

    @staticmethod
    def _match_score(discrepancies: list[Discrepancy]) -> float:
        if not discrepancies:
            return 100.0
        penalty = 0.0
        for d in discrepancies:
            penalty += {"low": 8.0, "medium": 18.0, "high": 30.0}.get(d.severity, 15.0)
        return max(0.0, round(100.0 - penalty, 1))


def _norm_tf(tf: str) -> str:
    t = (tf or "").strip().upper().replace(" ", "")
    aliases = {
        "4HOUR": "4H",
        "4HR": "4H",
        "H4": "4H",
        "1HOUR": "1H",
        "1HR": "1H",
        "H1": "1H",
        "15MIN": "15M",
        "15MINUTE": "15M",
        "M15": "15M",
    }
    return aliases.get(t, t)


def _norm_trend(trend: str) -> str:
    t = (trend or "").strip().lower()
    if t in {"bullish", "buy", "up", "bull"}:
        return "Bullish"
    if t in {"bearish", "sell", "down", "bear"}:
        return "Bearish"
    if t in {"range", "ranging", "consolidation", "sideways"}:
        return "Range"
    if not t or t == "unknown":
        return "Unknown"
    # Title-case passthrough
    raw = trend.strip()
    if raw in {"Bullish", "Bearish", "Range"}:
        return raw
    return "Unknown"


def _norm_structure(label: str) -> str:
    s = (label or "").upper().replace(" ", "").replace("_", "")
    if not s or s == "UNKNOWN":
        return "Unknown"
    if "HH" in s or "HIGHERHIGH" in s or s in {"BULLISH", "UP"}:
        return "HH"
    if "HL" in s or "HIGHERLOW" in s:
        return "HL"
    if "LL" in s or "LOWERLOW" in s or s in {"BEARISH", "DOWN"}:
        return "LL"
    if "LH" in s or "LOWERHIGH" in s:
        return "LH"
    return label.strip() or "Unknown"


def _structure_compatible(a: str, b: str) -> bool:
    bullish = {"HH", "HL"}
    bearish = {"LL", "LH"}
    if a in bullish and b in bullish:
        return True
    if a in bearish and b in bearish:
        return True
    return a == b


def _trend_from_closes(closes: list[float]) -> str:
    if len(closes) < 3:
        return "Unknown"
    first = sum(closes[: max(1, len(closes) // 3)]) / max(1, len(closes) // 3)
    last = sum(closes[-max(1, len(closes) // 3) :]) / max(1, len(closes) // 3)
    change = (last - first) / first if first else 0.0
    if change > 0.0015:
        return "Bullish"
    if change < -0.0015:
        return "Bearish"
    return "Range"


def _structure_from_closes(closes: list[float]) -> str:
    trend = _trend_from_closes(closes)
    if trend == "Bullish":
        return "HH"
    if trend == "Bearish":
        return "LL"
    return "Unknown"


def _price_close(a: float, b: float, tol_pct: float = PRICE_TOL_PCT) -> bool:
    if a == 0 and b == 0:
        return True
    base = max(abs(a), abs(b), 1e-9)
    return abs(a - b) / base * 100.0 <= tol_pct


def _candle_sequence_agree(visual_closes: list[float], market_closes: list[float]) -> bool:
    """Compare last N directional moves (up/down), not absolute prices."""
    n = min(len(visual_closes), len(market_closes), 12)
    if n < 3:
        return True
    v = visual_closes[-n:]
    m = market_closes[-n:]
    agree = 0
    total = 0
    for i in range(1, n):
        vd = v[i] - v[i - 1]
        md = m[i] - m[i - 1]
        if abs(vd) < 1e-12 and abs(md) < 1e-12:
            agree += 1
            total += 1
            continue
        if abs(vd) < 1e-12 or abs(md) < 1e-12:
            total += 1
            continue
        total += 1
        if (vd > 0 and md > 0) or (vd < 0 and md < 0):
            agree += 1
    if total == 0:
        return True
    return (agree / total) >= CANDLE_DIR_MIN_MATCH
