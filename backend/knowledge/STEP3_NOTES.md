# Knowledge Engine — Step 3 completion notes

## SSOT role

Vision / CV produce **candidates** only. The Knowledge Engine is the single
source of truth for marking a Smart Money Concept as **validated**.

- Brain `_build_bundle` calls `KnowledgeEngine.validate_concept` for each
  candidate before appending to `validated_concepts`.
- Cognitive pipeline already gates features via `validate_features` before
  Evidence.
- Relationships never set `strengthens_trade=True` and always note that they
  do not guarantee a trade.

## API hardening

| Path | Behavior |
|------|----------|
| `GET /api/knowledge/*?version=` | Unknown version → **404** (not 500) |
| `POST /api/knowledge/validate` | Concept + context |
| `POST /api/knowledge/validate/features` | FeatureCollection gate |

## Catalog v1.0

- `internal_liquidity` / `external_liquidity` use dedicated `feature_types`.
- Named `prefer_*` rules are soft; `require_*` map to declarative conditions.
- Mitigation → OB relationships restored (`consumes`, non-guaranteeing).

## Tests

See `tests/test_knowledge_engine.py` — catalog coverage, soft rules, API 404,
Brain knowledge wiring.
