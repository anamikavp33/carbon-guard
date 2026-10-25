# Carbon Guard: AI-Powered Carbon Credit Verification and Fraud Detection

Final-year B.Tech CSE project (academic prototype) by **Ameegha** (admin dashboard), **Amritha** (mobile app),
**Anamika** (backend) and **Antony** (database).

Users record environmental activities (tree plantation, solar panels, water harvesting) with a photo and GPS
location in a Flutter app. A FastAPI backend checks the evidence: AI image check, GPS and address, satellite
imagery, and duplicate/fraud-risk checks. Administrators review each submission in a React dashboard. Approved
activities earn project-defined **Green Credits**, and users have a **Trust Score**. Data lives in MongoDB Atlas.

> Green Credits are reward points of this project, **not** legally recognised carbon credits. AI, GPS and
> satellite results are evidence signals, not proof. An administrator makes every final decision.

## Start here

| Document | What it is |
|---|---|
| [PROJECT_STATUS.md](PROJECT_STATUS.md) | What works, what is tested, what is left: **read first** |
| [PROJECT_OVERVIEW.md](PROJECT_OVERVIEW.md) | Goals, decisions, assumptions, limitations |
| [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | Components, workflow and status diagrams, security |
| [API_CONTRACT.md](API_CONTRACT.md) | Every endpoint, field and status value, with real examples |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Collections, fields, indexes, integrity rules |
| [TEAM_RESPONSIBILITIES.md](TEAM_RESPONSIBILITIES.md) | Who owns what, integration checkpoints, review demos |
| [SETUP_GUIDE.md](SETUP_GUIDE.md) | Windows installation, running, testing, troubleshooting |

## Folders

```
carbon-guard/
├── backend/            FastAPI API, verification services, tests          (Anamika)
├── admin_dashboard/    React admin web app                                (Ameegha)
├── mobile_app/         Flutter Android app                                (Amritha)
├── database/           init, seed, cleanup, integrity scripts, examples   (Antony)
├── ai_model/           MobileNetV2 training + evaluation, weights folder  (Anamika + team)
└── docs/               project plan PDF goes here (docs/project_plan.pdf)
```

## Quick start (development, same laptop)

```bat
cd carbon-guard\backend
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env          (edit it: see SETUP_GUIDE.md)
uvicorn main:app --reload        (http://127.0.0.1:8000/docs)

cd ..\admin_dashboard
copy .env.example .env
npm install
npm run dev                      (http://localhost:5173)
```
Mobile app: see `mobile_app/README.md`.
