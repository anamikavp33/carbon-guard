"""End-to-end check against a RUNNING backend, over real HTTP (like the apps use it).

    python scripts/smoke_test.py --base-url http://127.0.0.1:8000 --admin-email admin@carbonguard.com

The admin password is read from the ADMIN_PASSWORD environment variable or .env (never typed
on the command line). It registers a throwaway user "smoke-<random>@example.com", submits a
synthetic image, waits for processing, approves it as admin and checks credits and Trust Score.
Run it against the in-memory database, or delete the test user afterwards
(database/seed/cleanup_demo_data.py --smoke).
"""
import argparse
import io
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402


def check(cond, msg):
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        sys.exit(1)


def synthetic_image() -> bytes:
    """A random-looking picture, so it never matches earlier test images."""
    img = Image.new("RGB", (320, 240), (40, 120, 40))
    d = ImageDraw.Draw(img)
    seed = uuid.uuid4().int
    for i in range(40):
        x, y = (seed >> (i * 3)) % 300, (seed >> (i * 2)) % 220
        d.rectangle([x, y, x + 20, y + 20], fill=((seed >> i) % 255, 100, (seed >> (i + 5)) % 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--admin-email", default=None)
    args = p.parse_args()

    from config import settings
    admin_email = args.admin_email or settings.ADMIN_EMAIL
    admin_password = settings.ADMIN_PASSWORD
    c = httpx.Client(base_url=args.base_url, timeout=60)

    health = c.get("/health").json()
    check(health["database"] == "connected", f"backend reachable, database connected ({health})")

    email = f"smoke-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post("/auth/register", json={"name": "Smoke Test", "email": email, "password": "smoke-test-pass"})
    check(r.status_code == 201, f"register {email}")
    tok = c.post("/auth/login", json={"email": email, "password": "smoke-test-pass"}).json()["access_token"]
    user = {"Authorization": f"Bearer {tok}"}
    start = c.get("/users/me", headers=user).json()

    lat, lng = 9.5 + (uuid.uuid4().int % 1000) / 10000, 76.3   # random-ish point in Kerala
    r = c.post("/submissions", headers=user,
               data={"activity_type": "tree_plantation", "latitude": lat, "longitude": lng,
                     "gps_accuracy_m": 8, "scale_value": 4, "description": "Smoke test (synthetic image)"},
               files={"image": ("smoke.jpg", synthetic_image(), "image/jpeg")})
    check(r.status_code == 201, f"submit activity -> {r.status_code} {r.json().get('status')}")
    sid = r.json()["id"]

    status = "processing"
    for _ in range(60):
        status = c.get(f"/submissions/{sid}/status", headers=user).json()["status"]
        if status != "processing":
            break
        time.sleep(1)
    check(status in ("pending", "manual_review"), f"processing finished with status '{status}'")
    detail = c.get(f"/submissions/{sid}", headers=user).json()
    print("     AI:", detail["ai_verification"]["status"], "| satellite:", detail["satellite_verification"]["status"],
          "| address:", detail["location_verification"]["address"], "| score:", detail["verification_score"])

    if not admin_password:
        print("SKIP admin steps: ADMIN_PASSWORD not set in the environment or .env")
        return
    r = c.post("/auth/login", json={"email": admin_email, "password": admin_password})
    check(r.status_code == 200, "admin login")
    admin = {"Authorization": "Bearer " + r.json()["access_token"]}
    queue = c.get(f"/admin/submissions?status={status}&search={email}", headers=admin).json()
    check(any(i["id"] == sid for i in queue["items"]), "submission is in the admin review queue")
    r = c.post(f"/admin/submissions/{sid}/approve", headers=admin, json={"notes": "Smoke test approval"})
    check(r.status_code == 200 and r.json()["status"] == "verified", "admin approved the submission")
    awarded = r.json()["green_credits_awarded"]

    after = c.get("/users/me", headers=user).json()
    check(after["green_credits_total"] == start["green_credits_total"] + awarded and awarded > 0,
          f"user credits {start['green_credits_total']} -> {after['green_credits_total']}")
    check(after["trust_score"] > start["trust_score"] or after["trust_score"] == 100,
          f"user trust score {start['trust_score']} -> {after['trust_score']}")
    check(c.post(f"/admin/submissions/{sid}/approve", headers=admin).status_code == 409, "second approval refused")
    print("ALL SMOKE CHECKS PASSED")


if __name__ == "__main__":
    main()
