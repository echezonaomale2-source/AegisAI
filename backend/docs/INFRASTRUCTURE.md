# Infrastructure (Step 1 — Production Roadmap)

Completes wiring, configuration, encryption, logging, and dependency injection
without redesigning the existing architecture.

## Configuration

`config/settings.py` (env prefix `AEGIS_`):

| Setting | Purpose |
|---------|---------|
| `storage_root` | Central storage directory |
| `log_level` / `log_to_file` | Structured logging |
| `cors_origins` | CORS allow list (`*` or CSV) |
| `encryption_key` | Optional Fernet key / passphrase |
| `encrypt_trade_records` | Encrypt `decision.json` at rest |
| `encrypt_memory_at_rest` | Encrypt SQLite narrative fields, cognitive archive, brain traces |
| `encrypt_charts` | Encrypt chart / outcome image bytes at rest |
| `min_confidence_threshold` | Brain gate default |

Example `.env`:

```
AEGIS_LOG_LEVEL=INFO
AEGIS_ENCRYPT_TRADE_RECORDS=true
AEGIS_ENCRYPT_MEMORY_AT_REST=true
AEGIS_ENCRYPT_CHARTS=true
AEGIS_CORS_ORIGINS=*
```

## Encryption

`core/security/encryption.py` — Fernet at-rest encryption.

- Trade `decision.json` encrypted when `encrypt_trade_records=true`
- Charts / outcomes encrypted with magic prefix `AEGENC1` when `encrypt_charts=true`
- Memory narratives + cognitive archive + brain traces when `encrypt_memory_at_rest=true`
- Text prefix `enc:v1:` preserves plaintext backward compatibility on read
- Key auto-created at `storage/.encryption_key` if unset
- Details: `memory/STEP7_NOTES.md`

## Logging

`core/logging_setup.py` — stderr + rotating file under `storage/logs/aegisai.log`.

HTTP middleware in `main.py` adds `X-Request-ID` and request timing logs.

## Dependency injection

`core/app_deps.py` — `AppServices` singleton used by FastAPI `Depends(...)`:

- `AnalysisService` / `AIBrain` / `TradeStore` / `MemoryService` / `Research*`

Routers no longer construct services at import time for the primary analyze/decide/brain paths.

## Frontend (paired)

- SecureStore-backed API URL config
- Encrypted `analysis_json` at rest
- Outcome sync queue for offline learning submits
- Settings: health check + API URL editor

## Quality gate

Unit tests: `tests/test_infrastructure.py`
