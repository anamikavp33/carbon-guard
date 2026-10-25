"""GPS checks.

GPS coordinates alone are NOT proof that an activity happened, and valid-looking coordinates
can still be faked. This module only checks that the location data is plausible and usable.
It does not detect GPS spoofing.
"""
from services import geocoding


def run_location_verification(lat: float, lng: float, accuracy_m, cfg: dict) -> dict:
    notes = []
    in_range = -90 <= lat <= 90 and -180 <= lng <= 180
    default_point = lat == 0 and lng == 0
    gps_valid = in_range and not default_point
    if default_point:
        notes.append("Coordinates are (0, 0), which is a default/empty GPS value.")
    if not in_range:
        notes.append("Coordinates are outside the valid range.")

    if accuracy_m is None:
        accuracy_ok = None
        notes.append("The device did not report GPS accuracy.")
    else:
        accuracy_ok = accuracy_m <= cfg["gps_max_accuracy_m"]
        if not accuracy_ok:
            notes.append(f"GPS accuracy is {accuracy_m:.0f} m, worse than the {cfg['gps_max_accuracy_m']} m limit.")

    geo = geocoding.reverse_geocode(lat, lng) if gps_valid else {"status": "skipped", "address": None}
    if geo["status"] == "unavailable":
        notes.append("Address lookup service was unavailable.")
    elif geo["status"] == "ok" and not geo["address"]:
        notes.append("No address found for these coordinates (for example open water or remote land).")

    return {
        "gps_valid": gps_valid,
        "accuracy_m": accuracy_m,
        "accuracy_ok": accuracy_ok,
        "address": geo["address"],
        "geocoding_status": geo["status"],
        "notes": notes,
    }
