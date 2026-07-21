"""
Confidence calibration — predicted confidence vs realized success.

Never drifts on a single trade. Requires accumulated samples per bin.
"""

from __future__ import annotations

from models.schemas import utc_now_iso
from memory.database import connect
from research.database import init_research_db
from research.models import CalibrationBin, CalibrationState

init_research_db()

# Minimum closed samples before adjustment factor moves.
MIN_SAMPLES_FOR_ADJUSTMENT = 25
MIN_BIN_SAMPLES = 8
MAX_FACTOR_STEP = 0.03  # per update batch
FACTOR_FLOOR = 0.75
FACTOR_CEILING = 1.15


class ConfidenceCalibrationEngine:
    def state(self) -> CalibrationState:
        with connect() as conn:
            rows = conn.execute(
                """
                SELECT bin_label, min_confidence, max_confidence, predictions, successes
                FROM research_calibration_bins
                ORDER BY min_confidence
                """
            ).fetchall()
            meta = {
                r["meta_key"]: r["meta_value"]
                for r in conn.execute("SELECT meta_key, meta_value FROM research_calibration_meta")
            }

        bins: list[CalibrationBin] = []
        weighted_gap = 0.0
        weight_sum = 0.0
        total_preds = 0
        for row in rows:
            preds = int(row["predictions"])
            succ = int(row["successes"])
            mid = (float(row["min_confidence"]) + float(row["max_confidence"])) / 2.0
            realized = (succ / preds) * 100.0 if preds > 0 else None
            gap = (mid - realized) if realized is not None else None
            bins.append(
                CalibrationBin(
                    bin_label=row["bin_label"],
                    min_confidence=row["min_confidence"],
                    max_confidence=row["max_confidence"],
                    predictions=preds,
                    successes=succ,
                    realized_rate=round(realized, 2) if realized is not None else None,
                    predicted_midpoint=mid,
                    calibration_gap=round(gap, 2) if gap is not None else None,
                )
            )
            if gap is not None and preds >= MIN_BIN_SAMPLES:
                weighted_gap += gap * preds
                weight_sum += preds
            total_preds += preds

        global_gap = (weighted_gap / weight_sum) if weight_sum else 0.0
        factor = float(meta.get("adjustment_factor", "1.0"))
        sample_count = int(meta.get("sample_count", "0"))

        # Expected Calibration Error (ECE) — weighted |predicted - realized|
        ece = None
        if total_preds > 0:
            ece_acc = 0.0
            for b in bins:
                if b.predictions <= 0 or b.realized_rate is None:
                    continue
                ece_acc += (b.predictions / total_preds) * abs(b.predicted_midpoint - b.realized_rate)
            ece = round(ece_acc, 2)

        notes = []
        if sample_count < MIN_SAMPLES_FOR_ADJUSTMENT:
            notes.append(
                f"Calibration warming up ({sample_count}/{MIN_SAMPLES_FOR_ADJUSTMENT} samples)."
            )
        elif abs(global_gap) >= 10:
            notes.append(
                f"AI is {'over' if global_gap > 0 else 'under'}confident by ~{abs(global_gap):.0f}%."
            )
        else:
            notes.append("Confidence roughly calibrated to historical outcomes.")
        if ece is not None:
            notes.append(f"Expected calibration error (ECE): {ece:.1f}%.")

        return CalibrationState(
            bins=bins,
            global_gap=round(global_gap, 2),
            sample_count=sample_count,
            adjustment_factor=round(factor, 4),
            expected_calibration_error=ece,
            last_updated=meta.get("last_updated"),
            notes=notes,
        )

    def record(self, predicted_confidence: float, *, success: bool) -> CalibrationState:
        """Incrementally update the matching confidence bin. Never overwrites history."""
        conf = max(0.0, min(100.0, float(predicted_confidence)))
        now = utc_now_iso()
        with connect() as conn:
            row = conn.execute(
                """
                SELECT bin_label FROM research_calibration_bins
                WHERE ? >= min_confidence AND ? < max_confidence
                LIMIT 1
                """,
                (conf, conf),
            ).fetchone()
            if row is None:
                # Clamp to top bin
                row = conn.execute(
                    "SELECT bin_label FROM research_calibration_bins ORDER BY min_confidence DESC LIMIT 1"
                ).fetchone()
            label = row["bin_label"]
            conn.execute(
                """
                UPDATE research_calibration_bins
                SET predictions = predictions + 1,
                    successes = successes + ?,
                    last_updated = ?
                WHERE bin_label = ?
                """,
                (1 if success else 0, now, label),
            )
            sample = int(
                conn.execute(
                    "SELECT meta_value FROM research_calibration_meta WHERE meta_key = 'sample_count'"
                ).fetchone()["meta_value"]
            )
            sample += 1
            conn.execute(
                "UPDATE research_calibration_meta SET meta_value = ? WHERE meta_key = 'sample_count'",
                (str(sample),),
            )
            conn.execute(
                """
                INSERT INTO research_calibration_meta (meta_key, meta_value) VALUES ('last_updated', ?)
                ON CONFLICT(meta_key) DO UPDATE SET meta_value = excluded.meta_value
                """,
                (now,),
            )
            conn.commit()

        # Recompute factor only after enough samples; small steps only.
        state = self.state()
        if state.sample_count >= MIN_SAMPLES_FOR_ADJUSTMENT:
            self._nudge_factor(state.global_gap)
            state = self.state()
        return state

    def adjust(self, predicted_confidence: float) -> float:
        """Apply gradual calibration factor — never one-trade swings."""
        state = self.state()
        if state.sample_count < MIN_SAMPLES_FOR_ADJUSTMENT:
            return float(predicted_confidence)
        adjusted = float(predicted_confidence) * state.adjustment_factor
        # Soft pull toward realized rate of the bin when bin is mature.
        for b in state.bins:
            if b.min_confidence <= predicted_confidence < b.max_confidence and b.realized_rate is not None:
                if b.predictions >= MIN_BIN_SAMPLES:
                    # Blend 85% adjusted prediction with 15% historical realized midpoint pull
                    adjusted = 0.85 * adjusted + 0.15 * b.realized_rate
                break
        return max(0.0, min(100.0, round(adjusted, 1)))

    def _nudge_factor(self, global_gap: float) -> None:
        """Positive gap = overconfident → reduce factor slightly."""
        with connect() as conn:
            row = conn.execute(
                "SELECT meta_value FROM research_calibration_meta WHERE meta_key = 'adjustment_factor'"
            ).fetchone()
            factor = float(row["meta_value"])
            step = 0.0
            if global_gap > 8:
                step = -MAX_FACTOR_STEP
            elif global_gap < -8:
                step = MAX_FACTOR_STEP
            elif abs(global_gap) > 4:
                step = -MAX_FACTOR_STEP * 0.4 if global_gap > 0 else MAX_FACTOR_STEP * 0.4
            factor = max(FACTOR_FLOOR, min(FACTOR_CEILING, factor + step))
            conn.execute(
                "UPDATE research_calibration_meta SET meta_value = ? WHERE meta_key = 'adjustment_factor'",
                (str(round(factor, 4)),),
            )
            conn.commit()
