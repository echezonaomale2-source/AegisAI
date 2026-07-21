# Reasoning Engine — Step 5 completion notes

## Role

Consume multi-TF `Evidence` → explainable `ReasoningReport`.

- Resolve conflicting evidence (items + structure lists)
- Detect missing evidence / empty timeframes
- Prefer **NO TRADE** when gates fail

## Gates (`gates_failed`)

| Gate | Meaning |
|------|---------|
| `no_usable_evidence` | Zero total weight |
| `image_uncertainty` | Uncertainty ≥ 55% |
| `inconclusive_mass` | Neutral / inconclusive mass |
| `min_evidence_score` | Primary score below threshold |
| `min_margin` | Buy vs sell margin too thin |
| `min_confidence` | Traceable confidence too low |
| `htf_conflict` | 4H opposes provisional side |
| `structure_stalemate` | Support/conflict too evenly matched |
| `missing_timeframes` | Multiple empty TFs |

## Explainability

- `narrative` — ordered reasons
- `explanation` — joined human-readable text
- `trace` — numeric confidence components
- `supporting_structures` / `conflicting_structures` rolled up from Evidence

## API

`POST /api/cognitive/reasoning/from-evidence`
