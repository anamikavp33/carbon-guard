"""Satellite evidence from Sentinel-2 (Copernicus Data Space Ecosystem, "CDSE").

What this does, when SATELLITE_PROVIDER=copernicus and credentials are set:
  1. Gets an access token for the OAuth client (client credentials).
  2. Searches the catalogue for the most recent Sentinel-2 L2A scene over the location in the
     last 120 days with less than 30% cloud cover.
  3. Downloads a true-colour picture of about 1 km x 1 km around the point (saved to uploads).
  4. For tree plantations only: computes the average NDVI (vegetation index, -1..1) of about
     300 m x 300 m around the point. Higher means more green vegetation.

Limits (also shown to admins):
  * Sentinel-2 pixels are 10 m. Single solar panels or water tanks are generally NOT visible,
    so for those activities the image is context only and earns no points.
  * One recent image cannot prove that trees were newly planted; NDVI only shows vegetation.
  * Clouds, image age and processing can make the evidence unavailable or misleading.

When not configured, or when the service fails, the result says so and earns no points.
Nobody's Trust Score is ever affected by satellite problems.
"""
import io
import json
import logging
import os
import time
import urllib.parse
from datetime import timedelta

from config import settings
from repositories.helpers import now
from services import http_client

log = logging.getLogger("carbon_guard")

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
CATALOG_URL = "https://sh.dataspace.copernicus.eu/api/v1/catalog/1.0.0/search"
PROCESS_URL = "https://sh.dataspace.copernicus.eu/api/v1/process"
SOURCE = "Sentinel-2 L2A (Copernicus Data Space Ecosystem)"
SEARCH_DAYS = 120
MAX_CLOUD = 30

TRUE_COLOR_SCRIPT = """//VERSION=3
function setup() { return { input: ["B02", "B03", "B04"], output: { bands: 3 } }; }
function evaluatePixel(s) { return [2.5 * s.B04, 2.5 * s.B03, 2.5 * s.B02]; }
"""

# Band 1: NDVI mapped from -1..1 to 0..255. Band 2: 255 where data exists, 0 where it does not.
NDVI_SCRIPT = """//VERSION=3
function setup() {
  return { input: ["B04", "B08", "dataMask"], output: { bands: 2, sampleType: "UINT8" } };
}
function evaluatePixel(s) {
  let ndvi = (s.B08 - s.B04) / (s.B08 + s.B04 + 0.000001);
  return [Math.round((ndvi + 1) * 127.5), s.dataMask * 255];
}
"""

_token = {"value": None, "expires": 0.0}


def _result(status: str, notes: list, **extra) -> dict:
    base = {"status": status, "source": None, "acquisition_date": None, "cloud_cover": None,
            "image_url": None, "ndvi_mean": None, "supports_claim": None, "notes": notes}
    base.update(extra)
    return base


def _get_token() -> str:
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": settings.CDSE_CLIENT_ID,
        "client_secret": settings.CDSE_CLIENT_SECRET,
    }).encode()
    data = http_client.request_json(TOKEN_URL, data=body, method="POST",
                                    headers={"Content-Type": "application/x-www-form-urlencoded"})
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + int(data.get("expires_in", 300))
    return _token["value"]


def _bbox(lat: float, lng: float, half_m: float) -> list:
    import math
    dlat = half_m / 111320.0
    dlng = dlat / max(math.cos(math.radians(lat)), 0.01)
    return [lng - dlng, lat - dlat, lng + dlng, lat + dlat]


def _find_scene(token: str, lat: float, lng: float):
    end = now()
    start = end - timedelta(days=SEARCH_DAYS)
    body = {
        "bbox": _bbox(lat, lng, 50),
        "datetime": f"{start:%Y-%m-%dT00:00:00Z}/{end:%Y-%m-%dT23:59:59Z}",
        "collections": ["sentinel-2-l2a"],
        "limit": 50,
        "filter": f"eo:cloud_cover < {MAX_CLOUD}",
        "filter-lang": "cql2-text",
    }
    data = http_client.request_json(CATALOG_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    scenes = [f["properties"] for f in data.get("features", []) if f.get("properties", {}).get("datetime")]
    if not scenes:
        return None
    return max(scenes, key=lambda p: p["datetime"])     # most recent


def _process(token: str, bbox: list, day: str, script: str, size: int) -> bytes:
    body = {
        "input": {
            "bounds": {"bbox": bbox, "properties": {"crs": "http://www.opengis.net/def/crs/EPSG/0/4326"}},
            "data": [{"type": "sentinel-2-l2a", "dataFilter": {
                "timeRange": {"from": f"{day}T00:00:00Z", "to": f"{day}T23:59:59Z"},
                "maxCloudCoverage": MAX_CLOUD}}],
        },
        "output": {"width": size, "height": size,
                   "responses": [{"identifier": "default", "format": {"type": "image/png"}}]},
        "evalscript": script,
    }
    return http_client.request_bytes(PROCESS_URL, data=json.dumps(body).encode(), method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json", "Accept": "image/png"})


def ndvi_mean_from_png(png: bytes):
    """Average NDVI of the pixels that have data, or None if no pixel has data."""
    from PIL import Image
    img = Image.open(io.BytesIO(png)).convert("LA")
    values = [v for v, mask in img.getdata() if mask > 0]
    if not values:
        return None
    return round(sum(values) / len(values) / 127.5 - 1.0, 3)


def run_satellite_verification(submission_id: str, lat: float, lng: float, activity_type: str, cfg: dict) -> dict:
    if settings.SATELLITE_PROVIDER != "copernicus":
        return _result("not_configured", ["Satellite imagery is not configured on this server."])
    try:
        token = _get_token()
        scene = _find_scene(token, lat, lng)
        if scene is None:
            return _result("no_recent_image", [
                f"No Sentinel-2 image with less than {MAX_CLOUD}% cloud in the last {SEARCH_DAYS} days."],
                source=SOURCE)
        day = scene["datetime"][:10]
        png = _process(token, _bbox(lat, lng, 500), day, TRUE_COLOR_SCRIPT, 256)
        folder = os.path.join(settings.UPLOAD_DIR, "satellite")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, f"{submission_id}.png"), "wb") as f:
            f.write(png)

        notes = ["Image covers about 1 km x 1 km centred on the submitted location (10 m pixels)."]
        ndvi, supports = None, None
        if activity_type == "tree_plantation":
            ndvi = ndvi_mean_from_png(_process(token, _bbox(lat, lng, 150), day, NDVI_SCRIPT, 64))
            if ndvi is None:
                notes.append("NDVI could not be computed (no valid pixels).")
            else:
                supports = ndvi >= cfg["satellite_min_ndvi"]
                notes.append(f"Average NDVI {ndvi} around the point "
                             f"({'at or above' if supports else 'below'} the {cfg['satellite_min_ndvi']} threshold). "
                             "NDVI shows vegetation, not that trees were newly planted.")
        else:
            notes.append("At 10 m resolution this activity is usually not visible; image shown as context only.")
        return _result("available", notes, source=SOURCE, acquisition_date=day,
                       cloud_cover=scene.get("eo:cloud_cover"), image_url=f"/uploads/satellite/{submission_id}.png",
                       ndvi_mean=ndvi, supports_claim=supports)
    except Exception as e:
        log.warning("Satellite evidence failed: %s", type(e).__name__)
        return _result("error", [f"Satellite service request failed ({type(e).__name__}). No penalty applied."],
                       source=SOURCE)
