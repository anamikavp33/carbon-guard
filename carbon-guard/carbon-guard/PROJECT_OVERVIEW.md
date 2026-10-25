# Carbon Guard: project overview

**Title:** AI-Powered Carbon Credit Verification and Fraud Detection Using Environmental Evidence
**Type:** Final-year B.Tech CSE project (academic prototype)
**Team:** Ameegha (admin dashboard), Amritha (mobile app), Anamika (backend), Antony (database)

## The problem

People can claim environmental activities with evidence that is wrong, reused or impossible to check.
A photo alone does not prove that an activity happened at the claimed place. Checking every claim by hand
is slow.

## What Carbon Guard does

1. A user records an activity in the **Flutter app**: tree plantation, solar panel installation or water
   harvesting. The record has a photo, GPS position, quantity and description.
2. The **FastAPI backend** stores the submission and runs automatic checks in the background:
   * **AI image check**: a fine-tuned MobileNetV2 model (when installed) recognises the activity in the photo.
   * **GPS check**: valid coordinates, the accuracy reported by the phone, a mock-location flag on Android, and
     a human-readable address from OpenStreetMap.
   * **Satellite evidence**: a recent Sentinel-2 image of the area and, for trees, a vegetation index (NDVI),
     when the Copernicus service is configured.
   * **Duplicate and fraud-risk checks**: the same file, similar-looking photos, nearby earlier submissions,
     too many submissions in a short time, unrealistic quantities, and the AI seeing a different activity.
3. The checks produce a **verification score** (0-100) with a plain-language explanation. The submission goes to
   a review queue: `pending` (recommended for approval) or `manual_review` (flagged or weak evidence).
4. An administrator reviews the evidence in the **React dashboard** and approves, rejects or sends it for manual
   review, optionally with a note to the user.
5. Approval awards **Green Credits** (project-defined reward points) exactly once, and adjusts the user's
   **Trust Score** (reputation, 0-100). Every change is recorded with its reason in **MongoDB**.

**No submission is ever approved automatically, and automatic checks never change credits or Trust Scores.**
Missing evidence (no AI model, no satellite) earns no points; it never counts as passed.

## What it does not claim

* Green Credits are **not** legally recognised carbon credits, and CO2 figures are **not** certified
  measurements. The CO2 factors are placeholders to be replaced with cited values.
* AI recognition, GPS and satellite images are **evidence signals, not proof**. GPS can be faked; the system
  does not detect all spoofing (only Android's own mock-location flag).
* Flags mean "a human should look", never "fraud proven".
* Accuracy figures for the AI model are only valid once measured with `ai_model/evaluation/evaluate.py`.

## Objectives and status

The live checklist is in `PROJECT_STATUS.md`. Summary:

| Objective | Status |
|---|---|
| Secure registration and login (bcrypt, JWT, roles) | Implemented and tested |
| Submit activities with photo, description, GPS | Backend tested; app written but not yet compiled |
| AI image analysis | Inference code tested; **no trained model yet** (needs dataset) |
| Location validation, duplicate and suspicious-submission detection | Implemented and tested |
| Satellite imagery as supporting evidence | Implemented and tested with a simulated service; **not yet run against the live Copernicus service** (needs a free account) |
| Verification score and manual-review routing | Implemented and tested |
| Admin approve / reject / manual review | Implemented and tested (API + dashboard integration) |
| Configurable Green Credits, awarded once | Implemented and tested |
| Trust Score with recorded reasons | Implemented and tested |
| User history, credit balance, Trust Score history | Backend tested; app screens written |
| Admin dashboards, review queue, users, reports, fraud alerts | Implemented; API integration tested; visual click-through still to do |

## Technology

Flutter (Dart) · React 18 + Vite (JavaScript) · Python 3.12 + FastAPI + Pydantic · MongoDB Atlas + PyMongo ·
bcrypt + JWT · Pillow + perceptual hashing · MobileNetV2 (TensorFlow for training, ONNX Runtime for inference) ·
OpenStreetMap Nominatim · Copernicus Sentinel-2 (Sentinel Hub API) · Git.

## Decisions made (and why)

| Decision | Reason |
|---|---|
| Admin decides every approval; checks only route to queues | Automated signals are not proof; prevents unearned credits and unfair penalties |
| Missing evidence = 0 points | The brief: missing evidence must not count as verified |
| Trust Score 0-100, starts at 50, changes only on admin decisions | Bounded, explainable, never penalises for service failures |
| Multipart image upload | Standard for mobile apps; about 33% smaller than base64 JSON |
| Background processing (`processing` status) | The app gets an answer immediately; slow services (satellite) do not block |
| MobileNetV2 → ONNX | Small and fast; backend needs only onnxruntime (works on Python 3.12/Windows) |
| Copernicus Data Space for satellite | Free account, Sentinel-2 imagery, documented API |
| Kept existing folder names (`admin_dashboard/`, flat `backend/`) | Working code and tests preserved; Flutter requires snake_case names anyway |
| Water harvesting measured in m³ | "Litres" made credits absurdly large (100,000 L = 400,000 credits) |
| Python 3.12 | Pinned packages have no builds for Python 3.15; 3.14 caused earlier MongoDB SSL problems |

## Assumptions to confirm against the project plan PDF

The PDF has not been provided, so these choices follow the master prompt and need checking:

1. Activity types are exactly tree plantation, solar panel installation and water harvesting.
2. Quantity units: trees, kW of panels, m³ of water storage.
3. Credit values (3 per tree, 5 per kW, 4 per m³) and CO2 factors (2.5, 50, 1 kg/year) are **placeholders**.
   Replace them with the plan's values or cited sources (`/admin/credit-rules`, `/admin/config`).
4. Score weights (AI 60, GPS 15, satellite 10, fraud checks 15) and the threshold of 70.
5. Trust Score rules (+5 approve, −10 reject, −15 reject after flags; start 50; range 0-100).
6. Endpoint names follow the master prompt's proposed list (plus a few additions, documented in API_CONTRACT.md).
7. Satellite provider: Copernicus Data Space (the plan may name Sentinel Hub or Google Earth Engine; the
   Copernicus service *is* Sentinel Hub's API on free infrastructure).

## Known limitations and future enhancements

| Limitation | Possible enhancement |
|---|---|
| No trained AI model yet | Collect the dataset, train, evaluate (see `ai_model/README.md`) |
| Satellite code not yet run against the live service; 10 m pixels cannot show single panels or tanks | Test with an account; before/after NDVI comparison for plantations; higher-resolution imagery |
| Images stored on the backend's disk, URLs public (but unguessable) | Cloud storage with signed URLs |
| Similar-image search compares every stored hash | Indexed similarity search for large data |
| Rate limiting is per process, in memory | Shared limiter (e.g. Redis) when running several servers |
| JWT has no refresh token or server-side logout | Refresh tokens, token revocation list |
| GPS spoofing detection limited to Android's mock flag | Compare photo EXIF location/time, device attestation |
| No password reset or email verification | Email-based flows |
| HTTP (not HTTPS) in development | HTTPS with a certificate when deployed |
