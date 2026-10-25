# Team responsibilities and integration guide

Everyone works against **two shared contracts**: `API_CONTRACT.md` (how apps talk to the backend) and
`DATABASE_SCHEMA.md` (what is stored). Change them only together, in one commit, and tell the team.

## Who owns what

| Member | Owns (edits freely) | Must coordinate before changing |
|---|---|---|
| **Ameegha**: admin dashboard | `admin_dashboard/` | API calls: add them only in `src/api.js`, following API_CONTRACT.md |
| **Amritha**: mobile app | `mobile_app/` | API calls: only in `lib/api/`, following API_CONTRACT.md |
| **Anamika**: backend | `backend/` (routes, services, models, tests), `ai_model/` | `API_CONTRACT.md` (with Ameegha + Amritha), field names (with Antony) |
| **Antony**: database | `database/`, `DATABASE_SCHEMA.md`, `backend/database.py` (indexes), `backend/repositories/` (with Anamika) | Collection and field names (with Anamika) |

## Integration table

| Module | Owner | Inputs | Outputs | Depends on | Done when |
|---|---|---|---|---|---|
| Database | Antony | Atlas account, `MONGO_URI` | Collections, indexes, demo data, backups | — | `check_db.py` SUCCESS; `init_db.py`, `seed_demo_data.py`, `check_integrity.py` run clean on Atlas |
| Backend API | Anamika | `.env`, database | REST API per API_CONTRACT.md, `/docs` | Database | `pytest` all pass; `smoke_test.py` passes against Atlas |
| AI model | Anamika (+ all for photos) | Labelled photos | `.onnx` + labels file, `results.md` | Backend | `evaluate.py` run on a separate test set; numbers recorded |
| Satellite | Anamika / Antony | Copernicus account | Evidence on submissions | Backend | A real submission shows a Sentinel-2 image and date |
| Admin dashboard | Ameegha | Backend URL, admin login | Review workflow, reports | Backend | `npm test` + integration test pass; every page clicked through |
| Mobile app | Amritha | Backend URL | Submissions from real phones | Backend | `flutter analyze` + `flutter test` pass; checklist in `mobile_app/README.md` done |
| End-to-end | All | Everything above | Demo | All | Flow below works on a real phone + dashboard + Atlas |

## Integration checkpoints

1. **Backend + Atlas:** Antony and Anamika put the Atlas URI in `backend/.env`. Run `check_db.py`, then start the
   backend, then run `smoke_test.py`.
2. **Dashboard:** Ameegha points `VITE_API_URL` at the backend and logs in as admin. Seed demo data
   (`seed_demo_data.py`) so every page has content. Click through all pages, approve one and reject one.
3. **Mobile:** Amritha runs `setup_android.ps1`, `flutter test`, then the emulator against the backend. Register,
   submit a tree photo, and watch it appear in the dashboard queue.
4. **Full flow on real devices** (do this before every review):
   register in the app → submit an activity → the record exists in Atlas (`check_integrity.py`) → the admin
   sees evidence and approves it → the app shows the new credits and Trust Score after refresh → the audit
   log shows the approval.

## How to work with Git

```bat
git checkout -b ameegha/settings-page         (one branch per task, named after you)
git add <files you changed>
git commit -m "Dashboard: settings page"
git push -u origin ameegha/settings-page      (then open a Pull Request on GitHub)
```
* Never commit `.env`, `node_modules/`, `venv/`, `uploads/`, model weights or datasets (`.gitignore` blocks them).
* Pull `main` every day: `git checkout main && git pull`.
* A Pull Request that changes `API_CONTRACT.md` must be approved by the backend owner **and** the affected client owner.

## What each member demonstrates at the review

| Member | Demo | Be ready to explain |
|---|---|---|
| Ameegha | Login, overview cards, review queue filters, a flagged submission (photo, map, AI, satellite, related duplicates), approve with confirmation and note, user search and history, credit rules, audit log | Protected routes, `api.js` single service layer, how errors and empty states are handled, why confirmations exist |
| Amritha | Onboarding, register, home, a submission with the camera and GPS (permission prompts), "Checking..." then the status, My submissions, detail with reasons, Trust/Credit history, logout | Secure token storage, permission handling, multipart upload, polling, error/retry states |
| Anamika | Swagger `/docs`, the submission pipeline, the scoring explanation, approve twice → refused, tests (`pytest`), AI evaluation results, satellite evidence | JWT + roles, background processing, why missing evidence earns 0, idempotent credits, limitations of AI/GPS/satellite |
| Antony | Atlas collections and indexes, a submission document, seed and cleanup, integrity check, backup with `mongodump` | Schema decisions, unique indexes preventing double awards, UTC times, why images are not stored in MongoDB |
