"""
Verification confidence influence.

Verification strengthens or weakens confidence — never replaces visual analysis.
"""

from __future__ import annotations

from verification.models import Discrepancy, VerificationStatus

# Caps — historical memory uses ±8; verification stays in a similar band.
MAX_BOOST = 5.0
MAX_PENALTY = 15.0

SEVERITY_PENALTY = {
    "none": 0.0,
    "low": 2.0,
    "medium": 5.0,
    "high": 8.0,
}


def influence_from_match(
    *,
    status: VerificationStatus,
    match_score: float,
    discrepancies: list[Discrepancy],
    significant: bool,
) -> float:
    """
    Compute signed confidence delta from verification outcome.

    screenshot_only / unavailable / error → 0 (no penalty for missing data)
    strong match → small boost
    conflicts → penalty scaled by severity (capped)
    """
    if status in {"screenshot_only", "unavailable", "error"}:
        return 0.0

    if status == "verified_match" and match_score >= 80:
        boost = MAX_BOOST * (match_score / 100.0)
        return round(min(MAX_BOOST, boost), 1)

    if status == "verified_partial" and not significant:
        # Mild agreement — tiny boost or flat
        if match_score >= 65:
            return round(min(3.0, MAX_BOOST * 0.5), 1)
        return 0.0

    # Conflict / significant disagreement
    penalty = 0.0
    for d in discrepancies:
        penalty += SEVERITY_PENALTY.get(d.severity, 4.0)
    if significant:
        penalty = max(penalty, 10.0)
    return round(-min(MAX_PENALTY, penalty), 1)
