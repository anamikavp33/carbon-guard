"""Green Credit rules (collection `green_credit_rules`). Credits = base x multiplier x scale_value."""
from database import get_db
from repositories.helpers import now

DEFAULT_RULES = {
    "tree_plantation": {"base_credit_value": 3.0, "impact_multiplier": 1.0},
    "solar_panel": {"base_credit_value": 5.0, "impact_multiplier": 1.0},
    "water_harvesting": {"base_credit_value": 4.0, "impact_multiplier": 1.0},
}


def ensure_defaults():
    for activity, rule in DEFAULT_RULES.items():
        get_db().green_credit_rules.update_one(
            {"activity_type": activity},
            {"$setOnInsert": {"activity_type": activity, **rule, "is_active": True,
                              "updated_by": None, "updated_at": now()}},
            upsert=True,
        )


def _public(d: dict) -> dict:
    return {k: d.get(k) for k in ("activity_type", "base_credit_value", "impact_multiplier",
                                  "is_active", "updated_by", "updated_at")}


def all_rules() -> dict:
    return {d["activity_type"]: _public(d) for d in get_db().green_credit_rules.find()}


def update(activity_type: str, changes: dict, admin_email: str) -> dict:
    get_db().green_credit_rules.update_one(
        {"activity_type": activity_type},
        {"$set": {**changes, "updated_by": admin_email, "updated_at": now()}},
    )
    return all_rules()[activity_type]
