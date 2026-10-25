# Carbon Guard system architecture

## Components

```mermaid
flowchart LR
    subgraph Clients
        APP["Flutter mobile app<br/>(users) - Amritha"]
        WEB["React admin dashboard<br/>(administrators) - Ameegha"]
    end

    subgraph Backend["FastAPI backend - Anamika"]
        API["REST API<br/>routes/ + Pydantic models/"]
        AUTH["Auth: bcrypt + JWT,<br/>roles checked on every call"]
        PIPE["Submission pipeline<br/>(background task)"]
        AI["AI check<br/>MobileNetV2 ONNX"]
        LOC["GPS check +<br/>reverse geocoding"]
        SAT["Satellite evidence<br/>Sentinel-2"]
        FRAUD["Duplicate / fraud-risk checks"]
        SCORE["Verification score<br/>+ explanation"]
        REVIEW["Admin decisions:<br/>credits + Trust Score"]
        FILES[("uploads/<br/>photos + satellite images")]
    end

    DB[("MongoDB Atlas<br/>Antony")]
    OSM["OpenStreetMap<br/>Nominatim"]
    CDSE["Copernicus Data Space<br/>(Sentinel Hub API)"]

    APP -- "HTTPS/HTTP + JWT<br/>JSON, multipart upload" --> API
    WEB -- "HTTP + JWT, JSON" --> API
    API --> AUTH
    API --> PIPE
    API --> REVIEW
    PIPE --> AI & LOC & SAT & FRAUD --> SCORE
    LOC --> OSM
    SAT --> CDSE
    PIPE --> FILES
    API -- PyMongo --> DB
    PIPE --> DB
    REVIEW --> DB
```

Rules:
* The app and the dashboard talk **only** to the API. Only the backend connects to MongoDB.
* All verification services live **inside the one backend** as separate modules (no microservices).
* The backend is the only authority for logins, roles, scores, credits and Trust Scores.

## Backend modules (`backend/`)

| Concern | Files |
|---|---|
| Settings from `.env` | `config.py` |
| Database connection, indexes, defaults | `database.py` |
| Login check, admin check | `auth_utils.py`, `services/auth_service.py`, `services/rate_limit.py` |
| API routes | `routes/auth.py`, `users.py`, `submissions.py`, `admin.py`, `info.py`, `views.py` |
| Request/response schemas | `models/common.py`, `user.py`, `submission.py`, `admin.py` |
| Data access (one file per collection group) | `repositories/users.py`, `submissions.py`, `ledger.py`, `credit_rules.py`, `config_store.py` |
| Image storage + hashing | `services/image_utils.py` |
| Submission pipeline | `services/pipeline.py` |
| AI verification | `services/ai_verification.py` |
| Location verification | `services/location_verification.py`, `services/geocoding.py` |
| Satellite evidence | `services/satellite.py` |
| Fraud detection | `services/fraud_detection.py` |
| Verification score | `services/verification_engine.py` |
| Admin decisions | `services/review.py` |
| Green Credits, Trust Score | `services/credits.py`, `services/trust.py` |
| External HTTP | `services/http_client.py` |

## Submission workflow

```mermaid
sequenceDiagram
    actor U as User (Flutter app)
    participant API as FastAPI
    participant BG as Background checks
    participant DB as MongoDB
    actor A as Admin (dashboard)

    U->>API: POST /submissions (photo, GPS, quantity) + JWT
    API->>API: validate fields, check the file is a real image (max 8 MB)
    API->>DB: insert submission, status "processing"
    API-->>U: 201 {id, status: "processing"}
    API->>BG: start checks
    BG->>BG: AI check, GPS + address, satellite, duplicate checks
    BG->>DB: save evidence, score, reasons, status pending / manual_review / rejected (bad GPS)
    loop every 2 s
        U->>API: GET /submissions/{id}/status
    end
    A->>API: GET /admin/submissions?status=pending
    A->>API: GET /admin/submissions/{id} (photo, map, evidence, flags)
    A->>API: POST /admin/submissions/{id}/approve {notes}
    API->>DB: status verified (only if still pending/manual_review)
    API->>DB: credit transaction (unique per submission), user balance += credits
    API->>DB: trust event (unique key), Trust Score +5 (max 100)
    API->>DB: audit log entry
    U->>API: GET /users/me → new balance and Trust Score
```

If any check crashes, the submission is kept and moved to `manual_review` with a note. Nobody is penalised.

## Status lifecycle

```mermaid
stateDiagram-v2
    [*] --> processing: user submits
    processing --> pending: score ≥ 70, no flags
    processing --> manual_review: flags, low score, missing evidence, or a check failed
    processing --> rejected: unusable GPS (no penalty)
    pending --> verified: admin approves (+credits, +5 trust)
    pending --> rejected: admin rejects (−10 trust)
    pending --> manual_review: admin asks for a closer look
    manual_review --> verified: admin approves
    manual_review --> rejected: admin rejects (−15 if flagged, else −10)
    rejected --> manual_review: admin reopens (penalty refunded)
    verified --> [*]
```

## Security measures

| Measure | Where |
|---|---|
| Passwords hashed with bcrypt, never returned | `services/auth_service.py`, models without `password_hash` |
| JWT (HS256), 24 h lifetime, secret only in `.env` | `services/auth_service.py`, `config.py` |
| Role read from the database on every request; deactivated users blocked | `auth_utils.py` |
| Admin endpoints check the role in the backend (not only hidden in the UI) | `routes/admin.py` (`require_admin`) |
| Other users' submissions return 404 | `routes/submissions.py` |
| Image validation: real JPEG/PNG/WEBP, max 8 MB, random file names | `services/image_utils.py` |
| Credits and trust events cannot be applied twice (unique indexes + atomic status change) | `database.py`, `repositories/submissions.set_status_if` |
| Login/register rate limit (10/min/IP) | `services/rate_limit.py` |
| Validation errors never echo submitted values; server errors are generic | `main.py` |
| CORS limited to configured dashboard origins | `main.py`, `CORS_ORIGINS` |
| Search input escaped (not a regex) | `repositories/helpers.contains` |
| Audit log of every admin action | `repositories/ledger.add_audit_log` |
| App token in Android encrypted storage | `mobile_app/lib/state/session.dart` |
| `.env`, uploads, model weights, backups ignored by Git | `.gitignore` |
