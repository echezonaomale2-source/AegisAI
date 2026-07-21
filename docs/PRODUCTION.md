"""
AegisAI — personal production checklist

## Done in-repo (you do not need to redo these)

- Architecture Phases 1–11 + FINAL ROADMAP Steps 1–15
- Encryption at rest (trades, charts, memory narratives, archive)
- Prefer NO TRADE; incremental learning; evaluation reports
- Analysis job crash recovery; SQLite integrity quarantine
- Dataset tooling (no fake labels)
- Backend `.env` created from `.env.example` (gitignored)
- CI workflow: `.github/workflows/backend-tests.yml`
- Smoke script: `backend/scripts/smoke_health.py`

## Required from you

### 1. Install Tesseract OCR (recommended)
Not found on PATH on this machine. Improves pair/timeframe reading from screenshots.

- Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
- Ensure `tesseract.exe` is on PATH, then restart the terminal / API.

### 2. Start the stack and connect the app
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --host 0.0.0.0 --port 8000
```
```powershell
cd frontend
npm install
npx expo start
```
In the app **Settings**, set API URL to your PC LAN IP, e.g. `http://192.168.x.x:8000`
(not `localhost` from a physical phone).

### 3. Run one real trade loop
Upload real 4H / 1H / 15M charts → review recommendation → submit TP or SL outcome →
confirm Insights + Memory update. Architecture tests cannot replace this.

### 4. Build your labeled dataset (quality loop)
```powershell
cd backend
python -m dataset import "C:\path\to\screenshots" --version v1
# Edit cv_datasets\v1\annotations.json — set labeled=true and fill Trend/BOS/etc.
python -m dataset validate --version v1
python -m dataset compare --version v1
```
Never invent labels; leave unlabeled until you annotate.

### 5. Back up secrets and storage
Periodically copy (offline drive / encrypted backup):

- `backend/storage/.encryption_key`  **critical — without it encrypted data is unreadable**
- `backend/storage/aegis_memory.db`
- `backend/storage/trades/`
- `backend/storage/cognitive_archive/`

### 6. Optional later
- Live market data provider (default is screenshot-only)
- YOLO / GPU vision (not required for personal v1)
- Expo production build (`eas build`) for installable APK/IPA
- Push git remote if you want cloud backup of **code** (never commit `.encryption_key` / `.env`)
