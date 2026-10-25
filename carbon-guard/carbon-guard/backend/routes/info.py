"""Read-only information that both apps can show to explain the rules to people."""
from fastapi import APIRouter, Depends
from auth_utils import get_current_user
from models.common import ACTIVITY_TYPES, STATUSES
from repositories import config_store, credit_rules
from services import ai_verification
from config import settings

router = APIRouter(prefix="/info", tags=["info"])

SCALE_UNITS = {
    "tree_plantation": "trees planted",
    "solar_panel": "kW of panels installed",
    "water_harvesting": "cubic metres (m³) of storage capacity",
}


@router.get("/rules")
def rules(current_user: dict = Depends(get_current_user)):
    cfg = config_store.get()
    credit = credit_rules.all_rules()
    return {
        "activity_types": [
            {"activity_type": a, "scale_unit": SCALE_UNITS[a],
             "credits_per_unit": round(credit[a]["base_credit_value"] * credit[a]["impact_multiplier"], 4)
             if credit[a]["is_active"] else 0.0,
             "max_scale": cfg["max_scale"][a]}
            for a in ACTIVITY_TYPES
        ],
        "statuses": STATUSES,
        "trust": {"initial": cfg["trust_initial"], "min": cfg["trust_min"], "max": cfg["trust_max"],
                  "rules": cfg["trust_rules"]},
        "evidence": {
            "ai_model_available": ai_verification.model_status()["available"],
            "satellite_configured": settings.SATELLITE_PROVIDER != "none",
        },
        "disclaimer": "Green Credits are reward points defined by this academic project. They are not "
                      "legally recognised carbon credits or certified carbon-offset measurements.",
    }
