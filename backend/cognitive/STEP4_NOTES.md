# Evidence Engine — Step 4 completion notes

## Role

Knowledge-validated `FeatureCollection` → structured `Evidence` with:

| Field | Purpose |
|-------|---------|
| Direction | BUY / SELL / NEUTRAL (never guessed) |
| Weight | Feature weight × confidence × image quality |
| Strength | Very Strong → Very Weak from confidence bands |
| Confidence | Pass-through from feature |
| Supporting structures | Aligned with dominant directional weight |
| Conflicting structures | Opposing directional items |

## Reports

`EvidenceEngine.report()` / `report_multi()` produce `EvidenceReport` summaries
for explainability and API consumers.

## API

`POST /api/cognitive/evidence/evaluate` — evaluate features → evidence + report.

## Pipeline

Unchanged: Vision → Reconstruction → Features → **Knowledge validate** →
Evidence → Reasoning. Evidence never invents structures; unknown direction
hints become **NEUTRAL**.
