# FINAL ROADMAP Steps 10–15 — completion notes

## Step 10 — Evaluation Engine
- Metrics: vision, features, knowledge, evidence, decisions, calibration (incl. ECE),
  trade reviews (+ decision quality distribution), learning (+ effectiveness proxy)
- Historical reports: `eval_reports` via `build_report(persist=True)` after outcomes
- Ground-truth mismatches: `record_false_detection` / `record_annotation_compare`
- API: `/api/evaluation/*`

## Step 11 — Testing Framework
- Module tests under `tests/`
- `pytest.ini` + `pytest-cov` in requirements
- Run: `pytest --cov --cov-report=term-missing`
- E2E smoke in `test_roadmap_steps_10_15.py`

## Step 12 — Dataset Support
- Package: `dataset/toolkit.py`
- CLI: `python -m dataset.toolkit import|validate|compare --version v1`
- API: `/api/dataset/import`, `/validate`, `/compare`
- **Never invents labels** — stubs only; compare uses human-labeled entries
- Storage: `cv_datasets/<version>/`

## Step 13 — Calibration
- Incremental bins + factor (≥25 samples, small steps)
- ECE exposed on `CalibrationState` / eval metrics
- BREAK_EVEN excluded from win/loss calibration

## Step 14 — Performance
- Vision/core/analysis cache eviction (LRU / max entries)
- Similarity: same-pair first, then broader scan
- Content-hash feature cache prevents duplicate image work

## Step 15 — Production Hardening
- Encryption: trades, charts, memory narratives, archive (Steps 1/7)
- `analysis_jobs` checkpoint + startup recovery of interrupted jobs
- SQLite `PRAGMA integrity_check` with corrupt quarantine
- `analysis_schema_version` on `decision.json`
- Corrupt trade dirs → `storage/trades_quarantine/`
