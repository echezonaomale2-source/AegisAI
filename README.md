# AegisAI

Personal AI smart-money trading assistant (**v12** — FINAL ROADMAP complete).

Phases 1–11 plus production Steps 1–15 are implemented: encryption, Knowledge/Evidence/Reasoning/Decision hardening, Memory/Learning, Research Insights, Evaluation, dataset tooling, calibration ECE, cache eviction, and crash recovery.

**Start here for personal production:** [docs/PRODUCTION.md](docs/PRODUCTION.md)

Phase history (architecture) remains below for reference.

## Stack

| Layer | Tech |
|---|---|
| Mobile | React Native (Expo SDK 54), TypeScript, React Navigation, React Native Paper, Reanimated |
| Local storage | Expo SQLite + Expo File System |
| Backend | FastAPI, Pydantic, OpenCV, NumPy, scikit-learn |
| Future AI | YOLOv8, PyTorch (optional) |

## Project layout

```
AIE/
├── frontend/          # Expo React Native app
│   └── src/
│       ├── components/
│       ├── screens/
│       ├── navigation/
│       ├── services/
│       ├── storage/
│       ├── hooks/
│       ├── types/
│       ├── utils/
│       └── theme/
└── backend/           # FastAPI AI service
    ├── api/
    ├── core/          # Phase 5.5: models / interfaces / services / pipeline / DI
    ├── cognitive/     # Phase 6: evidence / reasoning / decision / risk engines
    ├── research/      # Phase 7: calibration / reviews / patterns / dashboard
    ├── knowledge/     # Phase 8: versioned SMC concepts & validation rules
    ├── evaluation/    # Phase 9: metrics, health, quality gates, path logs
    ├── brain/         # Phase 10: AI Brain decision coordinator
    ├── verification/  # Phase 11: optional market data verification
    ├── models/
    ├── services/
    ├── decision/      # Phase 3: decision / confidence / risk / explanation
    ├── cv/            # Phase 5: vision engine / detectors / graph / cache / testing
    ├── memory/        # Phase 4/4.5: review / patterns / learning / lessons
    ├── vision/        # preprocess, ROI, candles (manual pair/TF labels)
    ├── ml/            # structure, liquidity, OB/FVG, zones
    ├── storage/       # uploads + persisted trade decisions
    ├── tests/
    └── config/
```

## App flow

Splash → Home (select pair + TFs → upload HTF / MTF / Entry charts → Analyze)
→ Analyzing → Results → History → Trade Details → Upload Outcome

Pair and timeframes are **user-selected**. The AI never reads symbol or TF text from screenshots.

## Run the backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://127.0.0.1:8000/docs  
Health: http://127.0.0.1:8000/api/health

**No OCR / Tesseract.** Install only Python deps from `requirements.txt`.

### Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/analyze` | App endpoint — multi extraction + decision engine → UI schema |
| POST | `/api/analyze/chart` | Single chart → structured SMC JSON |
| POST | `/api/analyze/multi` | 4H + 1H + 15M → three independent JSON analyses |
| POST | `/api/decide` | Full TradeDecision (bias, entry/SL/TP, explanation, warnings) |
| GET | `/api/trades` | List saved backend trade decisions |
| GET | `/api/trades/{id}` | Fetch one saved trade decision |
| POST | `/api/vision/chart` | Phase 5 single-chart visual understanding (features + graph) |
| POST | `/api/vision/multi` | Phase 5 multi-TF vision + relationship (no trade bias) |
| POST | `/api/cognitive/reason` | Phase 6 evidence + reasoning report + graded decision |
| GET | `/api/learning/summary` | Learning / calibration / pattern snapshot |
| GET | `/api/research/dashboard` | Insights: performance, calibration bins, patterns, memory |
| POST | `/api/dataset/import` | Import screenshots into versioned dataset (no auto-labels) |
| GET | `/api/dataset/{version}/validate` | Validate annotated dataset |
| POST | `/api/dataset/{version}/compare` | Compare AI detections vs human labels |
| GET | `/api/knowledge/concepts` | Phase 8 SMC concept definitions |
| POST | `/api/knowledge/validate` | Validate a concept against a context |
| GET | `/api/evaluation/dashboard` | Phase 9 system health + evaluation KPIs |
| GET | `/api/evaluation/report` | Full evaluation performance report |
| POST | `/api/evaluation/gates/check` | Quality gate (require measurable improvement) |
| POST | `/api/brain/recommend` | Phase 10 AI Brain recommendation + reason trace |
| POST | `/api/verification/check` | Phase 11 optional screenshot vs OHLC verification |
| GET | `/api/verification/discrepancies` | Stored verification discrepancies |
| GET | `/api/verification/health` | Verification layer health |

### Phase 11 notes

- Screenshot analysis remains primary and never requires market data.
- Pluggable `MarketDataProvider` (default `NullMarketDataProvider` = screenshot only).
- On mismatch: reduce confidence, warn, and store discrepancies — do not invent chart structure from OHLC.
- Docs: `backend/verification/ARCHITECTURE.md`.

### Phase 10 notes

- AI Brain is the single entry point for recommendations (`AnalysisService` → `AIBrain`).
- Never analyzes raw images; coordinates Vision, Knowledge, Evidence, Reasoning, Memory, Risk.
- Prefers NO TRADE when evidence is incomplete, HTFs conflict, confidence is weak, or risk is invalid.
- Historical memory influences confidence but does not override chart analysis alone.
- Full reason traces stored under `backend/storage/brain_traces/`.
- Docs: `backend/brain/ARCHITECTURE.md`.

### Phase 9 notes

- Evaluation Engine measures vision, features, knowledge, evidence, decisions, calibration, reviews, learning.
- Decision path logs store input → concepts → evidence → reasoning → decision → outcome.
- Module updates must pass quality gates / A/B tests before acceptance.
- Research screen shows overall system health grades.
- Docs: `backend/evaluation/ARCHITECTURE.md`, `backend/evaluation/METRICS.md`.

### Phase 8 notes

- Knowledge Engine stores SMC rules separately from AI logic (`backend/knowledge/`).
- Vision detects candidates → Knowledge validates → Evidence consumes only validated concepts.
- Incomplete validation returns **Unknown** — never guessed.
- Knowledge is versioned (current **1.0**); analyses stamp the version used.
- Docs: `backend/knowledge/ARCHITECTURE.md`, `backend/knowledge/CONCEPTS.md`.

### Phase 7 notes

- Post-trade review compares original analysis vs outcome; decision quality (Excellent→Avoid) is **not** win/loss.
- Confidence calibration uses historical bins; never drifts on a single trade.
- Pattern library tracks feature combinations with wins/losses/no-trade counts.
- Self-checks run before persist (evidence, conflicts, pattern reliability, calibrated confidence).
- Research screen in the app: Home → Research.
- Docs: `backend/research/ARCHITECTURE.md`.

### Phase 6 notes

- Nine independent engines: Vision → Reconstruction → Features → Evidence → Reasoning → Decision → Risk → Memory → Learning.
- Reasoning aggregates supporting / conflicting / missing evidence — never naive single-feature if/else for entries.
- Insufficient evidence, thin margins, high image uncertainty, HTF conflict, or bad RR → **NO TRADE**.
- Every decision includes a reproducible hash and confidence `trace`.
- Cognitive archive: `backend/storage/cognitive_archive/`.
- Feature weights (learning): `backend/storage/cognitive_feature_weights.json`.
- Architecture: `backend/cognitive/ARCHITECTURE.md`.

### Phase 5.5 notes

- Core package (`backend/core/`) separates image understanding from market reasoning.
- Canonical internal model: **ChartModel** — Decision / SMC / Learning never read raw images.
- Service layer: Image / Chart / Vision / Feature / SMC / Decision / Confidence / Memory / Learning / Similarity.
- Dependency injection via `ServiceContainer`; protocols allow future GPU/model swaps per module.
- Intermediate cache under `storage/core_cache/` (keyed by image hash + model version).
- Architecture doc: `backend/core/ARCHITECTURE.md`.

### Phase 5 notes

- Modular CV pipeline: validate → chart ROI → candles → SMC features → structure graph.
- Unknown features are marked Unknown — never invented.
- Feature cache avoids reprocessing unchanged screenshots (`storage/vision_cache`).
- Decision Engine still consumes `ChartAnalysis`; vision graph is available via `/api/vision/*`.
- Test harness:

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
python -m cv.testing.run_folder path\to\charts --out path\to\results
```

### Phase 4.5 notes

- Every closed trade runs a full case-study review (prediction vs reality).
- Scorecard: structure, liquidity, OB, FVG, entry, SL, TP, RR, overall (0–100).
- Self-critique answers the key correctness questions and stores strengths/weaknesses.
- Pattern database tracks named feature combinations (trades/wins/losses/avg RR/win rate).
- Learning is gated by review quality — weak (F/D) cases have minimal influence.
- Trade grades: A+ Excellent → F Avoid. NO TRADE remains a successful professional outcome.

### Phase 2 notes

- Each timeframe is analyzed independently first.
- Pair/timeframe return `Unknown` when not readable — never guessed.
- Poor image quality returns `Image Quality Too Low`.

### Phase 3 notes

- Top-down only: 4H → 1H → 15M.
- BUY requires bullish 4H + bullish 1H + 15M bullish confirmation.
- SELL requires bearish 4H + bearish 1H + 15M bearish confirmation.
- Otherwise returns **NO TRADE** (conflict, weak confidence, poor quality, unclear liquidity, missing confirmation, bad RR).
- Weighted confidence: 4H 30% · 1H 25% · 15M 20% · Liquidity 10% · OB 5% · FVG 5% · Structure 5%.
- Every decision is persisted under `backend/storage/trades/` with screenshots + features.
- No learning in this phase.

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path
pytest tests -q
```

## Run the mobile app

```powershell
cd frontend
copy .env.example .env
npm install
npx expo start
```

Then press `a` for Android emulator, `i` for iOS simulator, or scan the QR code with Expo Go.

### API URL for devices

Edit `frontend/.env`:

| Environment | `EXPO_PUBLIC_API_URL` |
|---|---|
| iOS simulator / web | `http://127.0.0.1:8000` |
| Android emulator | `http://10.0.2.2:8000` |
| Physical phone | `http://YOUR_LAN_IP:8000` |

Restart Expo after changing `.env`.

## Phase 1 scope

Included:

- All screens and navigation
- Dark trading UI (black / emerald / blue)
- Chart image pick + preview + replace (PNG/JPG/JPEG only)
- Analyze loading stages
- FastAPI placeholder analysis
- Permanent local history (SQLite + saved chart files)
- Trade details + outcome upload (TP / SL)

Not included (by design for personal v1):

- Auth / login / registration / multi-user cloud
- Notifications / payments
- Mandatory live market data (optional provider; default screenshot-only)
- YOLO / GPU vision (optional future)
- Classic indicators (RSI, EMA, MACD, Bollinger)
