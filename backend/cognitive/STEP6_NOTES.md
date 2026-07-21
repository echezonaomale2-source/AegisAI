# Decision Engine — Step 6 completion notes

## Output contract

Every decision includes:

| Field | Notes |
|-------|-------|
| Recommendation | BUY / SELL / **NO TRADE** |
| Entry / SL / TP / RR | Real levels or `—` (never invented) |
| Confidence | Post-risk, gated |
| Trade grade | A+ … F |
| Warnings | Conflicts, gates, risk notes |
| Detailed explanation | Evidence scores + levels + trail |
| `gates_applied` | Reasoning + decision/risk gates |
| `reproducible_hash` | Deterministic from inputs |

## Decision gates

| Gate | Effect |
|------|--------|
| Reasoning `gates_failed` | Surfaced as warnings |
| `risk_invalid` | Forces NO TRADE |
| `post_risk_confidence` | Forces NO TRADE |
| `incomplete_levels` | Forces NO TRADE if BUY/SELL lacks levels |

## API

`POST /api/cognitive/decision/from-reasoning`
