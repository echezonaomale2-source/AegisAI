"""Market Structure Detector — swings, HH/HL/LH/LL, trend, impulse, pullback."""

from __future__ import annotations

from cv.models import CandleOHLC, FeatureObject
from ml.structure_analyzer import analyze_market_structure
from ml.swing_detector import detect_swings, split_swings
from vision.candle_detector import Candle


class MarketStructureDetector:
    def detect(self, legacy_candles: list[Candle], candles: list[CandleOHLC]) -> list[FeatureObject]:
        if len(legacy_candles) < 5:
            return [
                FeatureObject(
                    id="trend_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Insufficient candles for structure."],
                )
            ]

        swings = detect_swings(legacy_candles)
        highs, lows = split_swings(swings)
        structure = analyze_market_structure(legacy_candles, swings)
        features: list[FeatureObject] = []

        # Label individual swings HH/HL/LH/LL from sequential comparison
        high_labels = _label_swings([s.price for s in highs], kind="high")
        low_labels = _label_swings([s.price for s in lows], kind="low")

        for i, s in enumerate(highs):
            label = high_labels[i] if i < len(high_labels) else None
            features.append(
                FeatureObject(
                    id=f"swing_high_{i}",
                    type="swing_high",
                    location={"index": s.index, "price": s.price, "structure_label": label},
                    confidence=78.0,
                    supporting_candles=[s.index],
                    label=label or "Swing High",
                )
            )
        for i, s in enumerate(lows):
            label = low_labels[i] if i < len(low_labels) else None
            features.append(
                FeatureObject(
                    id=f"swing_low_{i}",
                    type="swing_low",
                    location={"index": s.index, "price": s.price, "structure_label": label},
                    confidence=78.0,
                    supporting_candles=[s.index],
                    label=label or "Swing Low",
                )
            )

        ms = structure.market_structure
        ms_map = {
            "Higher Highs": "higher_high",
            "Higher High": "higher_high",
            "Higher Low": "higher_low",
            "Lower Lows": "lower_low",
            "Lower Low": "lower_low",
            "Lower High": "lower_high",
        }
        if ms in ms_map:
            last_swing = highs[-1] if "High" in ms and highs else (lows[-1] if lows else None)
            loc = {}
            if last_swing is not None:
                loc = {"index": last_swing.index, "price": last_swing.price}
            features.append(
                FeatureObject(
                    id="structure_primary",
                    type=ms_map[ms],  # type: ignore[arg-type]
                    location=loc,
                    confidence=structure.confidence.get("market_structure", 60.0),
                    supporting_candles=[c.index for c in legacy_candles[-5:]],
                    label=ms,
                    relationships=[f.id for f in features if f.type in {"swing_high", "swing_low"}][-4:],
                )
            )
        elif ms in {"Unknown", ""}:
            features.append(
                FeatureObject(
                    id="structure_unknown",
                    type="unknown",
                    confidence=0.0,
                    label="Unknown",
                    notes=["Market structure could not be detected confidently."],
                )
            )

        trend_type = "trend" if structure.trend in {"Bullish", "Bearish"} else (
            "range" if structure.trend == "Range" else "unknown"
        )
        features.append(
            FeatureObject(
                id="trend_primary",
                type=trend_type,  # type: ignore[arg-type]
                location={"trend": structure.trend},
                confidence=structure.confidence.get("trend", 0.0),
                supporting_candles=[c.index for c in legacy_candles[-8:]],
                label=structure.trend if structure.trend != "Unknown" else "Unknown",
                relationships=["structure_primary"] if any(f.id == "structure_primary" for f in features) else [],
            )
        )

        if structure.bos:
            features.append(
                FeatureObject(
                    id="bos_primary",
                    type="bos",
                    location={"side": structure.trend},
                    confidence=structure.confidence.get("bos", 70.0),
                    supporting_candles=[legacy_candles[-1].index],
                    label="Break Of Structure",
                    relationships=["trend_primary"],
                )
            )
        if structure.choch:
            features.append(
                FeatureObject(
                    id="choch_primary",
                    type="choch",
                    location={"side": structure.trend},
                    confidence=structure.confidence.get("choch", 70.0),
                    supporting_candles=[legacy_candles[-1].index],
                    label="Change Of Character",
                    relationships=["trend_primary"],
                )
            )
        if structure.impulse_move:
            features.append(
                FeatureObject(
                    id="impulse_primary",
                    type="impulse",
                    confidence=structure.confidence.get("impulse", 70.0),
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="Impulse Move",
                    relationships=["trend_primary"],
                )
            )
        if structure.correction_move:
            features.append(
                FeatureObject(
                    id="pullback_primary",
                    type="pullback",
                    confidence=65.0,
                    supporting_candles=[c.index for c in legacy_candles[-6:]],
                    label="Pullback",
                    relationships=["trend_primary"],
                )
            )
        if structure.strong_rejection or structure.weak_rejection:
            features.append(
                FeatureObject(
                    id="rejection_primary",
                    type="rejection",
                    confidence=structure.confidence.get("rejection", 60.0),
                    supporting_candles=[legacy_candles[-1].index],
                    label="Strong Rejection" if structure.strong_rejection else "Weak Rejection",
                    relationships=["trend_primary"],
                )
            )

        return features


def _label_swings(prices: list[float], *, kind: str) -> list[str | None]:
    """Sequential HH/HL or LH/LL labels for swing prices. Unknown when insufficient history."""
    labels: list[str | None] = []
    for i, price in enumerate(prices):
        if i == 0:
            labels.append(None)
            continue
        prev = prices[i - 1]
        if kind == "high":
            labels.append("HH" if price > prev else "LH")
        else:
            labels.append("HL" if price > prev else "LL")
    return labels
