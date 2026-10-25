"""Practical duplicate and suspicious-claim checks.

Flags only ask a human to look ("flagged for review"). A flag is NOT proof of fraud:
legitimate users can plant several trees at one spot, and photos of one site can look alike.
Reasons never name other users or their submission ids (admins see those ids separately).
"""
from datetime import timedelta
from repositories import submissions
from repositories.helpers import now
from services.ai_verification import ACTIVITY_CLASSES
from services.image_utils import hamming


def run_fraud_detection(user: dict, sub_id, image_hash: str, image_dhash: str, gps: dict,
                        activity_type: str, scale_value: float, ai: dict, cfg: dict) -> dict:
    flags, reasons, related = [], [], []
    sub_id = str(sub_id)

    # 1. exact duplicate image (identical file bytes)
    same = [s for s in submissions.find_by_hash(image_hash) if s["id"] != sub_id]
    if same:
        flags.append("duplicate_image")
        reasons.append(f"This exact image file was already submitted {len(same)} time(s).")
        related += [s["id"] for s in same]

    # 2. visually similar image (perceptual hash)
    limit = cfg["similar_image_max_distance"]
    similar = [sid for sid, h in submissions.all_dhashes()
               if sid != sub_id and sid not in related and hamming(image_dhash, h) <= limit]
    if similar:
        flags.append("similar_image")
        reasons.append(f"{len(similar)} earlier image(s) look very similar to this one.")
        related += similar

    # 3. same / nearby location
    radius = cfg["duplicate_location_radius_m"]
    near = submissions.nearby(gps["lat"], gps["lng"], radius, exclude_id=sub_id)
    if near:
        flags.append("duplicate_location")
        who = "this user" if all(n["user_id"] == user["id"] for n in near) else "other users"
        reasons.append(f"{len(near)} earlier submission(s) within {radius:g} m of this location (from {who}).")
        related += [n["id"] for n in near if n["id"] not in related]

    # 4. many submissions in a short time
    recent = submissions.count_recent_by_user(user["id"], now() - timedelta(minutes=10), exclude_id=sub_id)
    if recent >= cfg["max_submissions_per_10min"]:
        flags.append("rapid_submissions")
        reasons.append(f"{recent} other submissions in the last 10 minutes.")

    # 5. implausible activity details
    max_scale = cfg["max_scale"].get(activity_type)
    if max_scale and scale_value > max_scale:
        flags.append("implausible_scale")
        reasons.append(f"Claimed quantity {scale_value:g} is above the allowed maximum {max_scale:g} for this activity.")

    # 6. the phone itself reported a mock (fake) location provider (Android only; null if unknown)
    if gps.get("is_mocked") is True:
        flags.append("mock_location")
        reasons.append("The phone reported that the location came from a mock-location app.")

    # 7. the AI confidently sees a DIFFERENT activity than the one claimed
    if (ai.get("status") == "available" and ai.get("predicted_class") in ACTIVITY_CLASSES
            and ai["predicted_class"] != activity_type and ai["confidence"] >= cfg["ai_min_confidence"]):
        flags.append("activity_mismatch")
        reasons.append(f"The AI model sees '{ai['predicted_class']}' (confidence {ai['confidence']}), "
                       f"not the claimed '{activity_type}'.")

    return {
        "is_duplicate_image": "duplicate_image" in flags or "similar_image" in flags,
        "is_duplicate_location": "duplicate_location" in flags,
        "suspicious_pattern": any(f in flags for f in ("rapid_submissions", "implausible_scale", "activity_mismatch", "mock_location")),
        "flags": flags,
        "reasons": reasons,
        "related_submission_ids": related,
    }
