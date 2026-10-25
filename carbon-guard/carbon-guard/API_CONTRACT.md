# Carbon Guard API contract

This is the **single source of truth** for how the Flutter app (Amritha) and the React dashboard
(Ameegha) talk to the backend (Anamika). If code and this file disagree, it is a bug: fix one of them
and tell the team. Interactive docs with "Try it out" buttons: `http://127.0.0.1:8000/docs`.

The example responses below were captured from the real running backend (in-memory database).

## 1. General rules

| Rule | Value |
|---|---|
| Base URL (same PC) | `http://127.0.0.1:8000` |
| Base URL (Android emulator) | `http://10.0.2.2:8000` |
| Base URL (real phone, same Wi-Fi) | `http://<backend laptop IPv4>:8000` (start uvicorn with `--host 0.0.0.0`) |
| Body format | JSON, except `POST /submissions` which is `multipart/form-data` |
| Authentication | Header `Authorization: Bearer <access_token>` on every call except register, login, health |
| Token lifetime | `expires_in` seconds (default 86400 = 24 h). After that any call returns 401: log in again |
| Times | ISO 8601 UTC with `Z`, e.g. `2026-10-25T16:19:14.129000Z` |
| Ids | 24-character hex strings (MongoDB ObjectId) |
| Images | `image_url` is a path. Show it with `BASE_URL + image_url` |
| Lists that can grow | Return a **page**: `{"items": [...], "total": 12, "skip": 0, "limit": 50}`. Next page: `?skip=50&limit=50` |

### Errors

Every error is `{"detail": ...}`.

| Code | Meaning | `detail` |
|---|---|---|
| 400 | Bad request (e.g. not an image, email taken) | text |
| 401 | Not logged in, bad or expired token | text. Clients: clear the token and go to login |
| 403 | Logged in but not allowed (not admin, or account deactivated) | text |
| 404 | Not found, **or another user's submission** (ids cannot be probed) | text |
| 409 | Action not allowed in the current status (e.g. approve a verified submission) | text |
| 422 | A field is missing or invalid | list of `{"loc": ["body","password"], "msg": "...", "type": "..."}` |
| 429 | Too many login/register attempts from this IP in one minute | text |
| 500 | Server bug. Details are only in the server log | `"Internal server error. Please try again."` |

Show `detail` to the user when it is text. For 422, show `loc[last]: msg`.

## 2. Shared values (use exactly these strings)

**Activity types** (`activity_type`)

| Value | Label | `scale_value` means | Default max |
|---|---|---|---|
| `tree_plantation` | Tree plantation | number of trees planted | 1000 |
| `solar_panel` | Solar panel installation | kW of panels installed | 500 |
| `water_harvesting` | Water harvesting | cubic metres (m³) of storage capacity | 1000 |

**Submission status** (`status`)

| Value | Meaning | Who moves it |
|---|---|---|
| `processing` | Automatic checks are running (usually a few seconds) | backend |
| `pending` | Checks passed, no flags, score at/above threshold: **recommended** for approval | backend |
| `manual_review` | Needs a careful human look (flags, low score, missing evidence, or sent by an admin) | backend / admin |
| `verified` | Approved by an admin. Credits awarded | admin only |
| `rejected` | Rejected by an admin, or automatically for unusable GPS (0,0) | admin / backend |

```
processing ──► pending ───────┬──► verified   (approve)
     │            │           └──► rejected   (reject)
     │            ▼ (manual-review)
     ├──────► manual_review ──┬──► verified   (approve)
     │            ▲           └──► rejected   (reject)
     │            └─────────────── rejected   (manual-review = reopen, refunds the penalty)
     └──────► rejected (automatic: unusable GPS, no penalty)
```

**Fraud / review flags** (`fraud_check.flags`). A flag means "a human should look", never "fraud proven".

| Flag | Raised when |
|---|---|
| `duplicate_image` | The exact same image file was submitted before |
| `similar_image` | An earlier image looks very similar (perceptual hash) |
| `duplicate_location` | Earlier submission(s) within 50 m |
| `rapid_submissions` | 5+ other submissions by the same user in 10 minutes |
| `implausible_scale` | `scale_value` above the activity's maximum |
| `activity_mismatch` | The AI model confidently sees a different activity |
| `mock_location` | The phone reported a mock-location provider (Android only; does not catch all GPS spoofing) |

**Evidence statuses**

| Field | Values |
|---|---|
| `ai_verification.status` | `available` (model ran), `unavailable` (no model installed), `error` (model failed) |
| `location_verification.geocoding_status` | `ok`, `disabled`, `unavailable` (service down), `skipped` (invalid GPS) |
| `satellite_verification.status` | `not_configured`, `available`, `no_recent_image`, `error`, `skipped` |

**Trust events** (`event_type`): `verified_submission`, `rejected_submission`, `fraud_confirmed`, `review_reopened`.

## 3. Endpoints

| Method | Path | Auth | Used by |
|---|---|---|---|
| GET | `/health` | none | both, setup checks |
| POST | `/auth/register` | none | app |
| POST | `/auth/login` | none | app, dashboard |
| GET | `/auth/me` | user/admin | app, dashboard (role check after login) |
| GET | `/users/me` | user | app home + profile |
| GET | `/users/me/trust-history` | user | app |
| GET | `/users/me/credit-history` | user | app |
| GET | `/info/rules` | user/admin | app (explain rules), dashboard |
| POST | `/submissions` | user | app |
| GET | `/submissions/me` | user | app |
| GET | `/submissions/{id}` | owner or admin | app |
| GET | `/submissions/{id}/status` | owner or admin | app (polling) |
| GET | `/admin/submissions` | admin | dashboard |
| GET | `/admin/submissions/{id}` | admin | dashboard |
| POST | `/admin/submissions/{id}/approve` | admin | dashboard |
| POST | `/admin/submissions/{id}/reject` | admin | dashboard |
| POST | `/admin/submissions/{id}/manual-review` | admin | dashboard |
| GET | `/admin/users` | admin | dashboard |
| GET | `/admin/users/{id}` | admin | dashboard |
| PATCH | `/admin/users/{id}` | admin | dashboard |
| GET | `/admin/stats` | admin | dashboard |
| GET | `/admin/reports` | admin | dashboard |
| GET | `/admin/fraud-flags` | admin | dashboard |
| GET | `/admin/audit-logs` | admin | dashboard |
| GET | `/admin/credit-rules` | admin | dashboard |
| PUT | `/admin/credit-rules/{activity_type}` | admin | dashboard |
| GET / PUT | `/admin/config` | admin | dashboard |
| GET | `/uploads/<file>` | none (random file names) | both, to show images |

### 3.1 Auth

**POST `/auth/register`** → `201`

```json
{"name": "Asha", "email": "asha@example.com", "password": "at-least-8-chars"}
```
```json
{"id": "6ade2c016233689001c193a0", "name": "Asha", "email": "asha@example.com", "role": "user"}
```
Errors: 400 email already registered, 422 invalid email / password shorter than 8 or longer than 64, 429.
The role is always `user`; admins are created only from the backend `.env` on startup.

**POST `/auth/login`** → `200`

```json
{"email": "asha@example.com", "password": "at-least-8-chars"}
```
```json
{"access_token": "eyJhbGciOiJIUzI1NiIs...", "token_type": "bearer", "expires_in": 86400}
```
Errors: 401 wrong email or password, 403 account deactivated, 429.
The dashboard must call `GET /auth/me` next and refuse to continue unless `role == "admin"`.

**GET `/auth/me`** → `{"id", "name", "email", "role"}`

### 3.2 User profile

**GET `/users/me`**

```json
{
  "id": "6ade2c016233689001c193a0", "name": "Asha", "email": "asha@example.com", "role": "user",
  "trust_score": 55.0, "green_credits_total": 12.0, "is_active": true,
  "created_at": "2026-10-25T16:19:13.857000Z",
  "submission_counts": {"total": 1, "processing": 0, "pending": 0, "manual_review": 0, "verified": 1, "rejected": 0},
  "total_co2_estimate": 10.0
}
```

**GET `/users/me/trust-history`**

```json
{
  "trust_score": 55.0, "trust_min": 0, "trust_max": 100,
  "events": [
    {"id": "6ade2c036233689001c193a4", "submission_id": "6ade2c026233689001c193a1",
     "event_type": "verified_submission", "score_delta": 5.0, "score_after": 55.0,
     "reason": "An admin approved a submission.", "created_at": "2026-10-25T16:19:15.965000Z"}
  ]
}
```
Events are oldest first. `score_delta` is the change actually applied (after the 0-100 bounds).

**GET `/users/me/credit-history`**

```json
{
  "green_credits_total": 12.0,
  "transactions": [
    {"id": "6ade2c036233689001c193a3", "submission_id": "6ade2c026233689001c193a1",
     "type": "award", "amount": 12.0, "created_at": "2026-10-25T16:19:15.950000Z"}
  ]
}
```
Transactions are newest first.

**GET `/info/rules`**: activity types with units, credits per unit, max scale; statuses; trust rules;
whether the AI model and satellite are available; and the Green Credit disclaimer. Example:

```json
{
  "activity_types": [{"activity_type": "tree_plantation", "scale_unit": "trees planted", "credits_per_unit": 3.0, "max_scale": 1000}, "..."],
  "statuses": ["processing", "pending", "manual_review", "verified", "rejected"],
  "trust": {"initial": 50, "min": 0, "max": 100,
            "rules": {"verified_submission": 5, "rejected_submission": -10, "fraud_confirmed": -15}},
  "evidence": {"ai_model_available": false, "satellite_configured": false},
  "disclaimer": "Green Credits are reward points defined by this academic project. They are not legally recognised carbon credits or certified carbon-offset measurements."
}
```

### 3.3 Submissions (user app)

**POST `/submissions`** (multipart/form-data) → `201`

| Form field | Type | Required | Rule |
|---|---|---|---|
| `activity_type` | text | yes | one of the activity types |
| `latitude` | number | yes | -90 to 90 |
| `longitude` | number | yes | -180 to 180 |
| `scale_value` | number | yes | greater than 0 (see units above) |
| `gps_accuracy_m` | number | no | accuracy reported by the phone, metres |
| `gps_is_mocked` | `true`/`false` | no | Android `Position.isMocked`: location came from a mock-location app |
| `description` | text | no | max 500 characters |
| `image` | file | yes | JPEG, PNG or WEBP, max 8 MB |

```json
{"id": "6ade2c026233689001c193a1", "status": "processing", "updated_at": "2026-10-25T16:19:14.129000Z"}
```
Errors: 400 not a valid image / too large / empty, 401, 422 (field named in `loc`).
The checks run in the background. Poll `GET /submissions/{id}/status` every 2 seconds until the status
is not `processing` (normally a few seconds; longer if satellite imagery is enabled).

**GET `/submissions/me?skip=0&limit=50`** → page of submission summaries, newest first:

```json
{"items": [{"id": "6ade2c026233689001c193a1", "user_email": "asha@example.com", "activity_type": "tree_plantation",
            "status": "verified", "image_url": "/uploads/b3299...jpg", "verification_score": 30.0,
            "flags": [], "green_credits_awarded": 12.0, "created_at": "2026-10-25T16:19:14.129000Z"}],
 "total": 1, "skip": 0, "limit": 50}
```

**GET `/submissions/{id}/status`** → `{"id", "status", "updated_at"}`

**GET `/submissions/{id}`** → full detail (the owner's view):

```json
{
  "id": "6ade2c026233689001c193a1", "activity_type": "tree_plantation", "status": "verified",
  "image_url": "/uploads/b329949ac93f437793ce39f196066300.jpg",
  "gps": {"lat": 9.522, "lng": 76.3, "accuracy_m": 8.0, "is_mocked": false},
  "description": "Planted 4 mango saplings", "scale_value": 4.0,
  "ai_verification": {"status": "unavailable", "model": null, "predicted_class": null, "confidence": null,
                      "matched": null, "scores": {}, "warnings": ["No AI model file installed (see ai_model/README.md)."]},
  "location_verification": {"gps_valid": true, "accuracy_m": 8.0, "accuracy_ok": true,
                            "address": "Thumpoly, Ambalappuzha, Alappuzha, Kerala, 688008, India",
                            "geocoding_status": "ok", "notes": []},
  "satellite_verification": {"status": "not_configured", "source": null, "acquisition_date": null, "cloud_cover": null,
                             "image_url": null, "ndvi_mean": null, "supports_claim": null,
                             "notes": ["Satellite imagery is not configured on this server."]},
  "fraud_check": {"is_duplicate_image": false, "is_duplicate_location": false, "suspicious_pattern": false,
                  "flags": [], "reasons": []},
  "verification_score": 30.0,
  "score_components": {"ai": 0.0, "gps": 15.0, "satellite": 0.0, "fraud": 15.0},
  "decision_reasons": [
    "AI evidence: 0.0 of 60 points (AI model not available, so no AI evidence).",
    "GPS check: 15.0 of 15 points (valid coordinates with acceptable accuracy).",
    "Satellite: 0.0 of 10 points (no satellite evidence (not_configured)).",
    "Fraud checks: 15.0 of 15 points (no flags).",
    "Total score 30.0 of 100 (recommended for approval at 70+ with no flags).",
    "Result: manual review, because the evidence score is below the threshold."
  ],
  "environmental_impact": {"co2_estimate": 10.0, "unit": "kg_co2_per_year"},
  "green_credits_awarded": 12.0,
  "review_notes": "Photo and location look right.", "reviewed_at": "2026-10-25T16:19:15.950000Z",
  "created_at": "2026-10-25T16:19:14.129000Z", "updated_at": "2026-10-25T16:19:15.950000Z"
}
```
While `status` is `processing`, the four evidence objects are `null` and `verification_score` is `null`.
`environmental_impact` values are `null` until the submission is verified.
When satellite imagery is available, `satellite_verification.image_url` is a path such as
`/uploads/satellite/<id>.png`.

### 3.4 Admin: submissions

**GET `/admin/submissions`**: query parameters `status`, `activity_type`, `search` (part of the user's
email), `skip`, `limit` (max 200). Returns a page of summaries (same shape as `/submissions/me`).

**GET `/admin/submissions/{id}`**: the detail above **plus**:

```json
{
  "user_id": "6ade2c016233689001c193a0", "user_email": "asha@example.com", "user_name": "Asha",
  "user_trust_score": 55.0, "related_submission_ids": [], "image_hash": "fc1185...6bd7",
  "review_round": 0, "reviewed_by": "admin@example.com", "processing_error": null
}
```
`related_submission_ids` lists the earlier submissions that caused flags (open them to compare images).

**POST `/admin/submissions/{id}/approve`**, **`/reject`**, **`/manual-review`**

Optional body `{"notes": "text up to 1000 characters"}`. Response: the updated admin detail.

| Action | Allowed from | Effect |
|---|---|---|
| approve | `pending`, `manual_review` | → `verified`; credits awarded once; Trust +5 |
| reject | `pending`, `manual_review` | → `rejected`; Trust −10, or −15 (`fraud_confirmed`) if it had flags |
| manual-review | `pending` | → `manual_review`; no Trust change |
| manual-review | `rejected` | → `manual_review` (reopen); refunds exactly what that rejection took; `review_round` +1 |

Errors: 404 unknown id, 409 not allowed from the current status (message names the status).
Every action is recorded in the audit log. The dashboard must ask for confirmation before each action.

### 3.5 Admin: users

**GET `/admin/users?search=&skip=&limit=`**: page of
`{id, name, email, role, is_active, trust_score, green_credits_total, created_at}`.
`search` matches part of the name or email (case-insensitive, plain text).

**GET `/admin/users/{id}`**: the row above plus `submission_counts`, `recent_submissions` (20 newest
summaries), `trust_events` (oldest first) and `credit_transactions` (newest first).

**PATCH `/admin/users/{id}`** body `{"is_active": false}`: deactivates (or reactivates) an account.
A deactivated user cannot log in and existing tokens stop working (403). Admins cannot deactivate
themselves (400).

### 3.6 Admin: statistics and reports

**GET `/admin/stats`**

```json
{"total_users": 1, "active_users": 1, "total_submissions": 1,
 "by_status": {"processing": 0, "pending": 0, "manual_review": 0, "verified": 1, "rejected": 0},
 "by_activity": {"tree_plantation": 1, "solar_panel": 0, "water_harvesting": 0},
 "awaiting_review": 0, "total_credits_issued": 12.0, "total_co2_estimate": 10.0, "fraud_flagged": 0}
```
`total_users` counts role `user` only. `awaiting_review` = pending + manual_review.

**GET `/admin/reports`**

```json
{"by_activity": [{"activity_type": "tree_plantation", "submitted": 1, "verified": 1, "rejected": 0,
                  "credits_issued": 12.0, "co2_estimate_kg_per_year": 10.0}, "..."],
 "by_month": [{"month": "2026-10", "submitted": 1, "verified": 1, "credits_issued": 12.0}],
 "note": "CO2 figures are prototype estimates from this project's configurable factors, not certified carbon-offset measurements. Months are by submission date (UTC)."}
```
`by_month` covers the last 12 months; months with no submissions are left out.

**GET `/admin/fraud-flags?skip=&limit=`**: page of
`{id, submission_id, user_id, user_email, submission_status, flags, reasons, related_submission_ids, created_at}`.

**GET `/admin/audit-logs?skip=&limit=`**: page of
`{id, admin_id, admin_email, action, target_type, target_id, details, created_at}`.
`action` is one of `submission_approved`, `submission_rejected`, `submission_sent_to_review`,
`credit_rule_updated`, `config_updated`, `user_activated`, `user_deactivated`.

### 3.7 Admin: rules and settings

**GET `/admin/credit-rules`** → list of
`{activity_type, base_credit_value, impact_multiplier, is_active, updated_by, updated_at}`.

**PUT `/admin/credit-rules/{activity_type}`** body
`{"base_credit_value": 3, "impact_multiplier": 1, "is_active": true}` → the updated rule.
Credits for an approval = `base_credit_value × impact_multiplier × scale_value` (0 if the rule is inactive).
Changes apply to future approvals only; each award stores a snapshot of the rule it used.

**GET `/admin/config`** → all scoring settings (see section 4).
**PUT `/admin/config`**: send only the fields to change, e.g. `{"recommend_threshold": 75}`.
Unknown keys inside `trust_rules`, `impact_factors` or `max_scale` → 400.

## 4. Scoring rules (defaults; admins can change them via `/admin/config`)

These are **prototype rules defined by this project**, not validated science.

**Verification score** (0-100, per submission):

| Part | Points | How it is earned |
|---|---|---|
| AI | up to 60 | `confidence × 60`, only if the model is installed, predicts the claimed activity, and confidence ≥ 0.6 |
| GPS | 15 | valid coordinates with accuracy ≤ 100 m (7.5 if the phone sent no accuracy; 0 if worse or invalid) |
| Satellite | 10 | only tree plantation, only when imagery is available and mean NDVI ≥ 0.3 |
| Fraud checks | 15 | no flags at all |

Missing evidence earns **0** points; it is never counted as passed. Result: unusable GPS → `rejected`
(no penalty); any flag → `manual_review`; score ≥ 70 → `pending`; otherwise `manual_review`.
**No submission is ever verified without an admin.**

**Green Credits**: awarded once, only when an admin approves. Defaults per unit:
3 per tree, 5 per kW of solar, 4 per m³ of water storage, × multiplier 1.

**CO2 estimate** (shown, not certified): 2.5 per tree, 50 per kW, 1 per m³ (kg CO2/year). These are
**placeholder values** that the team must replace with cited figures before the final demo.

**Trust Score**: starts at 50, always between 0 and 100. Changes only on admin decisions:
approve +5, reject −10, reject a flagged submission −15, reopen refunds the earlier penalty.
Automatic checks, missing AI/satellite and server problems never change it.
