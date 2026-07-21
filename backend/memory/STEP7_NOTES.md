# Memory Engine — Step 7 completion notes

## At-rest encryption

Reuses Step 1 `LocalEncryptor` (Fernet).

| Asset | Mechanism | Setting |
|-------|-----------|---------|
| Trade `decision.json` | `enc:v1:` text | `encrypt_trade_records` |
| Chart / outcome images | `AEGENC1\0` + Fernet bytes | `encrypt_charts` |
| Cognitive archive JSON | `enc:v1:` text | `encrypt_memory_at_rest` |
| Brain reason traces | `enc:v1:` text | `encrypt_memory_at_rest` |
| SQLite narrative columns | `enc:v1:` per field | `encrypt_memory_at_rest` |

## SQLite policy

**Encrypted:** analyses, features JSON, explanation, lessons, reviews.

**Plaintext (for similarity / stats):** `trade_id`, pair, status, outcome,
direction, confidence, `fingerprint_bits`, `fingerprint_hash`, paths,
pattern keys, aggregate counters.

Plaintext rows remain readable (`enc:v1:` prefix is optional on decrypt).

## APIs / helpers

- `TradeStore.read_chart_bytes(path)` — decrypt chart for display
- `CognitiveMemoryEngine.load_archive(trade_id)` — decrypt archive
- `ReasonTraceStore.load(...)` — decrypt trace
- `memory.secure_fields` — seal/unseal helpers

## Env

```
AEGIS_ENCRYPT_TRADE_RECORDS=true
AEGIS_ENCRYPT_MEMORY_AT_REST=true
AEGIS_ENCRYPT_CHARTS=true
```
