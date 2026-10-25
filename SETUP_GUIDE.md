# Carbon Guard setup guide (Windows)

Commands are for **Command Prompt** (`cmd`). Where PowerShell differs, it is noted.
Never paste passwords, connection strings or API keys into chat, documents or Git. They go only in your
local `.env` files.

## 0. Install the tools (once per laptop)

| Tool | Who needs it | Get it | Check |
|---|---|---|---|
| Git | everyone | https://git-scm.com/download/win | `git --version` |
| Python **3.12** | backend, database, AI evaluation | https://www.python.org/downloads/ (3.12.x, tick "Add python.exe to PATH") | `py -3.12 --version` |
| Node.js 20 or newer (LTS) | dashboard | https://nodejs.org | `node -v` |
| Flutter (stable) + Android Studio | mobile app | https://docs.flutter.dev/get-started/install/windows/mobile | `flutter doctor` |
| MongoDB Database Tools (optional) | backups | https://www.mongodb.com/try/download/database-tools | `mongodump --version` |

**Why Python 3.12?** Some pinned packages have no builds for Python 3.15, and 3.14 caused MongoDB SSL
errors earlier. If `python --version` shows another version, that is fine: always create the environment with
`py -3.12` as below.

## 1. Backend (Anamika; everyone who runs the system)

```bat
cd carbon-guard\backend
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
notepad .env
```
PowerShell: activate with `venv\Scripts\Activate.ps1`. If scripts are blocked, run once:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

In `.env` set at least:

| Setting | Value |
|---|---|
| `JWT_SECRET_KEY` | output of `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ADMIN_EMAIL` | the admin login, a normal-looking address (not `.local` / `.test`) |
| `ADMIN_PASSWORD` | a strong password, known only to the team |
| `MONGO_URI` | the Atlas connection string (section 2) |
| `GEOCODING_CONTACT_EMAIL` | a team email (OpenStreetMap asks for one) |

Test the database, then start the server:

```bat
python scripts\check_db.py
uvicorn main:app --reload
```
Open http://127.0.0.1:8000/docs. `GET /health` should say `"database": "connected"`.

For phones and other laptops on the same Wi-Fi: `uvicorn main:app --host 0.0.0.0 --port 8000` and allow Python
in the Windows Firewall prompt (private networks only). Find the laptop IP with `ipconfig` (IPv4 Address).

**No Atlas yet?** Set `DB_MODE=memory` and run `pip install mongomock`. The data is lost when the server stops,
so use this only for development.

### Backend tests

```bat
pip install -r requirements-dev.txt
python -m pytest -q
```
The tests use an in-memory database and fake external services. They never touch Atlas or the internet.

End-to-end check against a running server (creates a throwaway user; clean it with
`..\database\seed\cleanup_demo_data.py --yes --smoke`):
```bat
python scripts\smoke_test.py --base-url http://127.0.0.1:8000
```

## 2. Database (Antony)

Full guide: `database/README.md`. Short version: create a free Atlas M0 cluster, a database user and a Network
Access entry for your IP, copy the connection string into `backend\.env`, then:

```bat
cd carbon-guard\backend
venv\Scripts\activate
python scripts\check_db.py
python ..\database\scripts\init_db.py
python ..\database\seed\seed_demo_data.py
python ..\database\scripts\check_integrity.py
```

## 3. Admin dashboard (Ameegha)

```bat
cd carbon-guard\admin_dashboard
copy .env.example .env
notepad .env          (VITE_API_URL=http://127.0.0.1:8000, or the backend laptop's IP)
npm install
npm run dev
```
Open http://localhost:5173 and log in with `ADMIN_EMAIL` / `ADMIN_PASSWORD`. If the dashboard runs on another
address, add it to `CORS_ORIGINS` in `backend\.env` and restart the backend.

Tests: `npm test`. Integration test against a running backend with demo data (Command Prompt):
```bat
set CG_INTEGRATION=1
set CG_ADMIN_EMAIL=admin@carbonguard.com
set CG_ADMIN_PASSWORD=<your admin password>
set VITE_API_URL=http://127.0.0.1:8000
npx vitest run src/integration.test.js
```
(PowerShell: `$env:CG_INTEGRATION="1"` and so on.) It approves and rejects submissions, so use demo data only.

Production build: `npm run build` → static files in `dist\`.

## 4. Mobile app (Amritha)

1. Install Flutter: download the stable SDK zip, extract it to `C:\src\flutter`, add `C:\src\flutter\bin` to PATH,
   install Android Studio (with Android SDK, platform tools and an emulator), then run
   `flutter doctor --android-licenses` and `flutter doctor` until Android shows a green tick.
2. Generate the Android files and permissions (PowerShell):
   ```powershell
   cd carbon-guard\mobile_app
   powershell -ExecutionPolicy Bypass -File setup_android.ps1
   flutter analyze
   flutter test
   ```
3. Start an emulator (Android Studio → Device Manager) or plug in a phone with USB debugging.
4. Run:
   ```bat
   flutter run
   flutter run --dart-define=API_BASE_URL=http://192.168.1.20:8000     (real phone; use your laptop IP)
   ```
More details and a first-run checklist: `mobile_app/README.md`.

## 5. Satellite evidence (optional)

1. Register at https://dataspace.copernicus.eu (free).
2. Open the Sentinel Hub dashboard (https://shapps.dataspace.copernicus.eu/dashboard/) → *User settings* →
   *OAuth clients* → *Create*. Copy the client id and secret (the secret is shown once).
3. In `backend\.env`: `SATELLITE_PROVIDER=copernicus`, `CDSE_CLIENT_ID=...`, `CDSE_CLIENT_SECRET=...`.
4. Restart the backend and submit a tree plantation. The admin detail page shows a Sentinel-2 image, its date
   and the NDVI. Free accounts have monthly processing quotas, so use it for demos, not bulk tests.

The code follows the documented Copernicus APIs and is tested with a simulated service, but it has **not yet been
run against the live service**. Record the first real run in `PROJECT_STATUS.md`.

## 6. AI model (optional until trained)

See `ai_model/README.md`: collect photos, train in Google Colab, copy the two files into `ai_model\weights\`,
restart the backend, run `evaluation\evaluate.py`.

## 7. Make a ZIP for sharing

From the folder that **contains** `carbon-guard`, in PowerShell:
```powershell
cd carbon-guard
git archive --format=zip --output ..\Carbon_Guard_Complete_Project.zip HEAD
```
`git archive` includes only committed files, so `.env`, `venv`, `node_modules`, uploads and weights are left out
automatically. Commit first. Without Git, zip by hand and **delete** `.env`, `venv`, `node_modules`,
`backend\uploads\*`, `mobile_app\build` and `.dart_tool` from the copy.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Configuration problem(s)` when the backend starts | The message names the missing or invalid `.env` value |
| `Could not start the database` / SSL handshake error | `python scripts\check_db.py`; use Python 3.12; add your IP in Atlas *Network Access*; try a phone hotspot (some college networks block Atlas) |
| `ModuleNotFoundError` | The virtual environment is not active (`venv\Scripts\activate`), or run `pip install -r requirements.txt` again |
| `pip` fails building Pillow/numpy | You are on Python 3.14/3.15. Delete `venv` and recreate it with `py -3.12 -m venv venv` |
| Dashboard: "Cannot reach the backend" | Backend not running, wrong `VITE_API_URL`, or the dashboard address is missing from `CORS_ORIGINS` |
| Dashboard login says "not an administrator" | Use the `ADMIN_EMAIL` account; normal users use the app |
| App: "Cannot reach the server" | See `mobile_app/README.md` (IP address, `--host 0.0.0.0`, firewall) |
| 429 "Too many attempts" | Wait one minute (login rate limit) |
| Port 8000 in use | `uvicorn main:app --reload --port 8001` and update the clients' URLs |
| Every submission goes to manual review | Expected while no AI model is installed (AI earns 0 points). See `ai_model/README.md` |
| Address shows "unavailable" | No internet, or OpenStreetMap is rate-limiting; set `GEOCODING_CONTACT_EMAIL` |
