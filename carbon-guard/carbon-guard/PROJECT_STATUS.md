# Carbon Guard: project status

Last updated: 2026-10-25 (final checks and packaging).

## Specification source

`docs/project_plan.pdf` is **not in the repository**. The working specification is the
"Master Project Prompt" provided by the team. Assumptions that still need confirmation
against the PDF are listed in `PROJECT_OVERVIEW.md` (section "Assumptions to confirm").

## Package

* **ZIP:** `Carbon_Guard_Complete_Project.zip` in the project root (`carbon-guard\`). It contains a
  `carbon-guard/` folder with 130 files: all source code, tests, documentation and `.env.example` templates.
* **Not included, on purpose:** real `.env` files (none exist), `venv/`, `node_modules/`, `dist/`, caches,
  uploaded images, AI model weights and datasets. Recreate them with `SETUP_GUIDE.md`.
* Built from the files Git does not ignore (`git ls-files --cached --others --exclude-standard`). Git is
  initialised but **no commit has been made yet**: the team should make the first commit.

## Final test results (run on 2026-10-25, Windows 11, Python 3.12.10, Node 24.13.1)

| Suite | Command | Result |
|---|---|---|
| Backend unit + API tests (in-memory DB, fake external services) | `python -m pytest` in `backend/` | **65 passed**, 0 failed, 0 skipped |
| Backend end-to-end over HTTP (running server, in-memory DB) | `python scripts/smoke_test.py` | **All 10 checks passed** (register, upload, background checks, admin queue, approve, credits 0 → 12, trust 50 → 55, second approval refused) |
| Dashboard unit tests | `npm test` | **7 passed**; 6 integration tests **skipped** in this run (they need a live backend) |
| Dashboard integration tests against a live backend | `npx vitest run src/integration.test.js` with `CG_INTEGRATION=1` | **6 passed** (login, stats/reports, approve/reject/reopen, user search + deactivate/reactivate, fraud flags + audit log, credit rules + settings) |
| Dashboard production build | `npm run build` | **Succeeded** |
| CORS | preflight from `http://localhost:5173` / another origin | Allowed / refused, as configured |
| AI evaluation script | `ai_model/evaluation/evaluate.py` with a tiny fake model | **Runs correctly**; the numbers mean nothing (fake model) |
| Android manifest setup script | `setup_android.ps1 -ManifestOnly` on a sample manifest | Adds permissions once; a second run changes nothing; written without BOM |
| **Flutter app** | `flutter analyze`, `flutter test` | **NOT RUN: Flutter is not installed on this PC.** The code has never been compiled |
| MongoDB Atlas | `scripts/check_db.py` | **NOT RUN: no `backend/.env` with a connection string exists** |
| Satellite (live Copernicus) | — | **NOT RUN: no account/credentials.** Tested only with a simulated service |
| Reverse geocoding (live OpenStreetMap) | smoke test with geocoding on | Worked on 2026-10-25 (returned real Kerala addresses) |
| Dashboard visual click-through in a browser | — | **NOT DONE** (no browser automation available). API behaviour behind every page is tested |

## What is complete

- [x] Backend (FastAPI): auth (bcrypt, JWT, roles, rate limit, deactivation), profile and histories, multipart
      upload, background processing, AI inference (ONNX), GPS + address, mock-location flag, satellite module,
      duplicate/fraud checks, explained score, admin review (approve / reject / manual review / reopen),
      credits once, bounded Trust Score, audit log, stats, reports, credit rules, settings.
- [x] Database: schema document, indexes, init / seed (synthetic) / cleanup / integrity scripts, examples, backup guide.
- [x] Admin dashboard: all pages listed in `admin_dashboard/README.md`, with confirmations, empty/error/loading states.
- [x] Flutter app source: all screens in `mobile_app/README.md`, tests written. **Untested.**
- [x] AI: training script (Colab) and evaluation script; fallback when no model exists.
- [x] Shared documents: README, PROJECT_OVERVIEW, SYSTEM_ARCHITECTURE (Mermaid diagrams), API_CONTRACT,
      DATABASE_SCHEMA, TEAM_RESPONSIBILITIES, SETUP_GUIDE.

## Still incomplete (in priority order)

1. **Compile and test the Flutter app** (Amritha): install Flutter, run `setup_android.ps1`, `flutter analyze`,
   `flutter test`, then the checklist in `mobile_app/README.md`. Expect to fix small compile issues.
2. **Connect MongoDB Atlas** (Antony + Anamika): create `backend/.env`, run `scripts/check_db.py`, `init_db.py`,
   `seed_demo_data.py`, `check_integrity.py`, then `smoke_test.py` against the Atlas-backed server.
3. **Click through the dashboard** in a browser, including a phone-width window (Ameegha).
4. **Train and evaluate the AI model** (needs about 150+ labelled photos per class; `ai_model/README.md`).
   Until then every submission gets 0 AI points and goes to manual review.
5. **Try satellite evidence with a real Copernicus account** (`SETUP_GUIDE.md` section 5) and record the result.
6. Confirm the assumptions in `PROJECT_OVERVIEW.md` against the project plan PDF; replace the placeholder
   credit values and CO2 factors with cited figures.
7. Make the first Git commit and push to a private GitHub repository.

## Setup in short

See `SETUP_GUIDE.md`. Backend: `py -3.12 -m venv venv`, `pip install -r requirements.txt`,
`copy .env.example .env` (fill it in), `uvicorn main:app --reload`. Dashboard: `npm install`, `npm run dev`.
App: `setup_android.ps1`, then `flutter run --dart-define=API_BASE_URL=http://<backend-ip>:8000`.

## Known limitations

Listed in full in `PROJECT_OVERVIEW.md`. In short: no trained AI model yet; satellite untested live and
unable to see single panels/tanks; GPS spoofing detection limited to Android's mock flag; Green Credits and
CO2 figures are project placeholders, not certified values; images stored on the backend disk; in-memory rate
limiting; no refresh tokens or password reset; HTTP in development.
