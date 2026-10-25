"""Submission lifecycle, step by step:

  1. create_submission(): validate + store the image, save the record with status "processing".
     The API answers the app immediately.
  2. process_submission() runs in the background: AI, GPS + address, satellite, fraud checks,
     score. The record moves to "pending", "manual_review" or "rejected".
  3. If anything crashes, the record is kept and moved to "manual_review" with a note,
     so no submission is ever lost and nobody is penalised for a server problem.
"""
import logging
import os
from bson import ObjectId

from config import settings

from repositories import config_store, ledger, submissions
from repositories.helpers import now, to_oid
from services import (ai_verification, fraud_detection, image_utils, location_verification, satellite,
                      verification_engine)

log = logging.getLogger("carbon_guard")


def create_submission(user: dict, activity_type: str, lat: float, lng: float, accuracy_m, is_mocked,
                      description, scale_value: float, raw_image: bytes) -> dict:
    image = image_utils.save_image(raw_image)      # may raise ImageError
    t = now()
    doc = {
        "_id": ObjectId(),
        "user_id": to_oid(user["id"]),
        "user_email": user["email"],
        "activity_type": activity_type,
        "image_filename": image.filename,
        "image_url": image.url,
        "image_hash": image.sha256,
        "image_dhash": image.dhash,
        "image_width": image.width,
        "image_height": image.height,
        "gps": {"lat": lat, "lng": lng, "accuracy_m": accuracy_m, "is_mocked": is_mocked},
        "description": description,
        "scale_value": scale_value,
        "status": "processing",
        "ai_verification": None,
        "location_verification": None,
        "satellite_verification": None,
        "fraud_check": None,
        "verification_score": None,
        "score_components": {},
        "decision_reasons": [],
        "processing_error": None,
        "environmental_impact": {"co2_estimate": None, "unit": None},
        "green_credits_awarded": 0.0,
        "review_round": 0,
        "reviewed_by": None,
        "review_notes": None,
        "reviewed_at": None,
        "created_at": t,
        "updated_at": t,
    }
    return submissions.insert(doc)


def process_submission(submission_id: str):
    record = submissions.get(submission_id)
    if record is None or record["status"] != "processing":
        return
    try:
        _run_checks(record)
    except Exception:
        log.exception("Processing failed for submission %s", submission_id)
        submissions.set_status_if(submission_id, ["processing"], {
            "status": "manual_review",
            "processing_error": "Automatic checks could not be completed. A human must review this submission.",
            "decision_reasons": ["Result: manual review, because the automatic checks failed (server problem). "
                                 "No Trust Score penalty."],
            "updated_at": now(),
        })


def _run_checks(record: dict):
    cfg = config_store.get()
    sid, gps = record["id"], record["gps"]
    user = {"id": record["user_id"], "email": record["user_email"]}
    image_path = os.path.join(settings.UPLOAD_DIR, record["image_filename"])

    ai = ai_verification.run_ai_verification(image_path, record["activity_type"], cfg["ai_min_confidence"])
    location = location_verification.run_location_verification(gps["lat"], gps["lng"], gps.get("accuracy_m"), cfg)
    if location["gps_valid"]:
        sat = satellite.run_satellite_verification(sid, gps["lat"], gps["lng"], record["activity_type"], cfg)
    else:
        sat = satellite._result("skipped", ["Skipped because the GPS coordinates are not usable."])
    fraud = fraud_detection.run_fraud_detection(user, sid, record["image_hash"], record["image_dhash"], gps,
                                                record["activity_type"], record["scale_value"], ai, cfg)
    decision = verification_engine.decide(ai, location, sat, fraud, cfg)

    submissions.set_status_if(sid, ["processing"], {
        "status": decision["status"],
        "ai_verification": ai,
        "location_verification": location,
        "satellite_verification": sat,
        "fraud_check": fraud,
        "verification_score": decision["score"],
        "score_components": decision["components"],
        "decision_reasons": decision["reasons"],
        "updated_at": now(),
    })
    if fraud["flags"]:
        ledger.add_fraud_log(sid, record["user_id"], fraud["flags"], fraud["reasons"], fraud["related_submission_ids"])
