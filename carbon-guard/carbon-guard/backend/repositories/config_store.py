"""Verification, trust and impact settings, stored in MongoDB so an admin can change them.

These are PROTOTYPE rules defined by this project. They are not scientifically validated
and are not an official carbon-market standard. They are explained in API_CONTRACT.md
(section "Scoring rules").
"""
import copy
from database import get_db

DEFAULT_CONFIG = {
    # Verification score points (total 100). Missing evidence earns 0 points, never full points.
    "weights": {"ai": 60, "gps": 15, "fraud": 15, "satellite": 10},
    # Score >= this and no flags -> "pending" (recommended for approval). Otherwise "manual_review".
    # An admin still makes every final decision.
    "recommend_threshold": 70,
    "ai_min_confidence": 0.6,            # below this the AI result does not "match" the claim
    "gps_max_accuracy_m": 100,           # GPS accuracy worse than this earns no GPS points
    "duplicate_location_radius_m": 50,
    "similar_image_max_distance": 8,     # dHash Hamming distance (0-64)
    "max_submissions_per_10min": 5,
    # Units: trees, kW of panels, cubic metres (m3) of water storage.
    "max_scale": {"tree_plantation": 1000, "solar_panel": 500, "water_harvesting": 1000},
    "satellite_min_ndvi": 0.3,           # tree plantation: mean NDVI needed for satellite points
    "trust_initial": 50,
    "trust_min": 0,
    "trust_max": 100,
    # Applied ONLY when an admin makes a decision. Automatic checks never change the Trust Score.
    "trust_rules": {
        "verified_submission": 5,
        "rejected_submission": -10,
        "fraud_confirmed": -15,
    },
    # kg CO2 per year per unit. PLACEHOLDER values for the prototype, not an official method:
    # the team must replace them with cited figures (see PROJECT_OVERVIEW.md, assumptions).
    "impact_factors": {
        "tree_plantation": 2.5,
        "solar_panel": 50.0,
        "water_harvesting": 1.0,
    },
}


def ensure_defaults():
    get_db().settings.update_one(
        {"key": "verification"}, {"$setOnInsert": {"key": "verification", **DEFAULT_CONFIG}}, upsert=True
    )


def get() -> dict:
    doc = get_db().settings.find_one({"key": "verification"}) or {}
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    for k, v in doc.items():
        if k in cfg:   # unknown or outdated keys in the database are ignored
            if isinstance(cfg[k], dict):
                cfg[k].update({kk: vv for kk, vv in v.items() if kk in cfg[k]})
            else:
                cfg[k] = v
    return cfg


def update(changes: dict) -> dict:
    current = get()
    for k, v in changes.items():
        if isinstance(current[k], dict):
            current[k].update(v)
        else:
            current[k] = v
    get_db().settings.update_one({"key": "verification"}, {"$set": current}, upsert=True)
    return current
