"""Combines the evidence into a verification score and a recommendation, and explains both.

The automatic checks never award credits and never change a Trust Score. They only decide
which review queue a submission goes to:

  * rejected       : hard rule failed (unusable GPS). No Trust Score penalty.
  * manual_review  : any fraud flag, or score below the recommend threshold.
  * pending        : score at/above the threshold and no flags ("recommended for approval").

An admin approves or rejects every pending / manual_review submission.
Missing evidence (AI model not installed, satellite not configured...) earns 0 points:
it is never counted as if it had passed. The weights are prototype values, not validated science.
"""


def decide(ai: dict, location: dict, satellite: dict, fraud: dict, cfg: dict) -> dict:
    w = cfg["weights"]

    if ai.get("status") == "available" and ai.get("matched"):
        ai_points = round(ai["confidence"] * w["ai"], 1)
        ai_text = f"image matches the claimed activity (confidence {ai['confidence']})"
    elif ai.get("status") == "available":
        ai_points, ai_text = 0.0, "image does not match the claimed activity well enough"
    else:
        ai_points, ai_text = 0.0, "AI model not available, so no AI evidence"

    if not location["gps_valid"]:
        gps_points, gps_text = 0.0, "invalid coordinates"
    elif location["accuracy_ok"] is None:
        gps_points, gps_text = round(w["gps"] / 2, 1), "valid coordinates, accuracy not reported (half points)"
    elif location["accuracy_ok"]:
        gps_points, gps_text = float(w["gps"]), "valid coordinates with acceptable accuracy"
    else:
        gps_points, gps_text = 0.0, "valid coordinates but poor accuracy"

    if satellite.get("supports_claim") is True:
        sat_points, sat_text = float(w["satellite"]), "satellite vegetation index supports the claim"
    elif satellite.get("status") == "available":
        sat_points, sat_text = 0.0, "satellite image available as context, does not add evidence"
    else:
        sat_points, sat_text = 0.0, f"no satellite evidence ({satellite.get('status')})"

    fraud_points = 0.0 if fraud["flags"] else float(w["fraud"])
    fraud_text = "flags raised: " + ", ".join(fraud["flags"]) if fraud["flags"] else "no flags"

    score = round(ai_points + gps_points + sat_points + fraud_points, 1)
    threshold = cfg["recommend_threshold"]
    reasons = [
        f"AI evidence: {ai_points} of {w['ai']} points ({ai_text}).",
        f"GPS check: {gps_points} of {w['gps']} points ({gps_text}).",
        f"Satellite: {sat_points} of {w['satellite']} points ({sat_text}).",
        f"Fraud checks: {fraud_points} of {w['fraud']} points ({fraud_text}).",
        f"Total score {score} of 100 (recommended for approval at {threshold}+ with no flags).",
    ]

    if not location["gps_valid"]:
        status = "rejected"
        reasons.append("Result: rejected automatically, because the GPS coordinates are not usable. "
                       "No Trust Score penalty. An admin can reopen it.")
    elif fraud["flags"]:
        status = "manual_review"
        reasons.append("Result: manual review, because flags need a human check. A flag is not proof of fraud.")
    elif score >= threshold:
        status = "pending"
        reasons.append("Result: pending admin approval (recommended for approval).")
    else:
        status = "manual_review"
        reasons.append("Result: manual review, because the evidence score is below the threshold.")

    return {
        "score": score,
        "status": status,
        "components": {"ai": ai_points, "gps": gps_points, "satellite": sat_points, "fraud": fraud_points},
        "reasons": reasons,
    }
