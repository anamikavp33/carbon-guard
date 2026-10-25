"""Reverse geocoding (coordinates -> human-readable place) with OpenStreetMap Nominatim.

Nominatim usage policy: at most 1 request per second, an identifying User-Agent, and
results should be cached. We cache by coordinates rounded to 4 decimals (about 11 m).
If the service is disabled or unreachable, the result says so; it is never an error
for the user and never lowers anyone's Trust Score.
"""
import logging
import threading
import time
import urllib.parse

from config import settings
from database import get_db
from repositories.helpers import now
from services import http_client

log = logging.getLogger("carbon_guard")
_lock = threading.Lock()
_last_call = 0.0


def _user_agent() -> str:
    contact = settings.GEOCODING_CONTACT_EMAIL or "no-contact-configured"
    return f"CarbonGuard-StudentProject/1.0 ({contact})"


def reverse_geocode(lat: float, lng: float) -> dict:
    """Returns {"status": "ok"|"disabled"|"unavailable", "address": str|None}."""
    if not settings.GEOCODING_ENABLED:
        return {"status": "disabled", "address": None}
    key = f"{round(lat, 4)},{round(lng, 4)}"
    cached = get_db().geocode_cache.find_one({"key": key})
    if cached:
        return {"status": "ok", "address": cached["address"]}

    global _last_call
    query = urllib.parse.urlencode({"lat": lat, "lon": lng, "format": "jsonv2", "zoom": 16})
    try:
        with _lock:   # respect 1 request/second
            wait = 1.0 - (time.monotonic() - _last_call)
            if wait > 0:
                time.sleep(wait)
            _last_call = time.monotonic()
            data = http_client.request_json(f"{settings.NOMINATIM_URL}?{query}",
                                            headers={"User-Agent": _user_agent()})
    except Exception as e:
        log.warning("Reverse geocoding failed: %s", type(e).__name__)
        return {"status": "unavailable", "address": None}

    address = data.get("display_name")
    if not address:   # e.g. open sea: Nominatim returns {"error": "Unable to geocode"}
        return {"status": "ok", "address": None}
    get_db().geocode_cache.update_one({"key": key}, {"$set": {"key": key, "address": address, "created_at": now()}},
                                      upsert=True)
    return {"status": "ok", "address": address}
