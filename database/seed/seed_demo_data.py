"""Fill the database with SYNTHETIC demo data, using the backend's own code.

    cd carbon-guard\\backend
    venv\\Scripts\\activate
    python ..\\database\\seed\\seed_demo_data.py

What it creates (all clearly marked as demo data):
  * 3 demo users  demo.asha@example.com, demo.ben@example.com, demo.chitra@example.com
    (field `is_demo: true`). Password: DEMO_USER_PASSWORD from the environment/.env, otherwise a
    random one that is printed once.
  * 8 submissions with computer-drawn pictures (not real photos), run through the real checks
    (AI, GPS + address, duplicate detection...), then some approved/rejected by the admin account, so
    the dashboards show every status, credits, Trust Score history, fraud flags and audit logs.

Nothing here is real evidence or real people. Remove it all with cleanup_demo_data.py.
Running it twice does not duplicate anything: existing demo users are skipped.
"""
import io
import os
import secrets
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

from PIL import Image, ImageDraw  # noqa: E402

DEMO_USERS = [
    ("Asha Demo", "demo.asha@example.com"),
    ("Ben Demo", "demo.ben@example.com"),
    ("Chitra Demo", "demo.chitra@example.com"),
]


def draw(kind: str, variant: int) -> bytes:
    """A simple synthetic picture: trees, solar panels or a water tank. Labelled 'SYNTHETIC DEMO'."""
    img = Image.new("RGB", (640, 480), (135, 190, 235))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 300, 640, 480], fill=(110 + variant * 7, 160, 80))
    if kind == "tree_plantation":
        for i in range(3 + variant):
            x = 60 + i * 110 + variant * 9
            d.rectangle([x + 22, 250, x + 38, 330], fill=(110, 75, 40))
            d.ellipse([x - 10, 150 - (i % 2) * 20, x + 70, 260], fill=(30, 120 + variant * 10, 40))
    elif kind == "solar_panel":
        d.polygon([(80, 300), (560, 300), (500, 140 + variant * 6), (140, 140 + variant * 6)], fill=(25, 45, 110))
        for i in range(1, 6):
            d.line([(80 + i * 80, 300), (140 + i * 60, 140 + variant * 6)], fill=(200, 200, 220), width=2)
    else:
        d.rectangle([220, 140 + variant * 5, 420, 360], fill=(70, 110, 160))
        d.ellipse([220, 120 + variant * 5, 420, 170 + variant * 5], fill=(90, 140, 190))
        d.line([(420, 200), (520, 200), (520, 120)], fill=(80, 80, 80), width=8)
    d.text((10, 10), "SYNTHETIC DEMO IMAGE - NOT REAL EVIDENCE", fill=(0, 0, 0))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


# (user index, activity, lat, lng, scale, image key, admin action, note)
PLAN = [
    (0, "tree_plantation", 9.9312, 76.2673, 12, ("tree_plantation", 1), "approve", "Saplings visible; location plausible."),
    (0, "solar_panel", 10.0159, 76.3419, 3, ("solar_panel", 1), None, None),
    (0, "water_harvesting", 9.5916, 76.5222, 6, ("water_harvesting", 1), "approve", "Tank matches the description."),
    (1, "tree_plantation", 11.2588, 75.7804, 12, ("tree_plantation", 1), None, None),        # same image as Asha
    (1, "solar_panel", 8.5241, 76.9366, 4, ("solar_panel", 2), "reject", "Panels look like a stock photo."),
    (1, "water_harvesting", 0.0, 0.0, 2, ("water_harvesting", 2), None, None),                 # unusable GPS
    (2, "tree_plantation", 10.5276, 76.2144, 5000, ("tree_plantation", 3), "reject", "Quantity not credible."),
    (2, "water_harvesting", 10.8505, 76.2711, 10, ("water_harvesting", 3), None, None),
]


def run_seed(password: str) -> int:
    """Create the demo users and submissions. Returns how many demo users were created (0 = already seeded)."""
    from config import settings
    import database
    from repositories import submissions
    from repositories import users as users_repo
    from services import pipeline, review
    from services.auth_service import hash_password

    db = database.get_db()
    database.init_db()
    admin = users_repo.get_by_email(settings.ADMIN_EMAIL)

    accounts, created = [], 0
    for name, email in DEMO_USERS:
        u = users_repo.get_by_email(email)
        if u is None:
            u = users_repo.create(name, email, hash_password(password), role="user", trust_score=50)
            db.users.update_one({"email": email}, {"$set": {"is_demo": True}})
            created += 1
        accounts.append(u)
    if created == 0:
        return 0

    for ui, activity, lat, lng, scale, (kind, variant), action, note in PLAN:
        user = accounts[ui]
        rec = pipeline.create_submission(user, activity, lat, lng, 12.0, False, f"Demo {activity.replace('_', ' ')}",
                                         scale, draw(kind, variant))
        pipeline.process_submission(rec["id"])
        if action == "approve":
            review.approve(admin, rec["id"], note)
        elif action == "reject":
            review.reject(admin, rec["id"], note)
        final = users_repo.get_by_id(user["id"])
        print(f"  {user['email']:<26} {activity:<17} -> {submissions.get(rec['id'])['status']:<14}"
              f"(trust {final['trust_score']}, credits {final['green_credits_total']})")
    return created


def main():
    from config import settings
    import database

    settings.validate()
    if settings.DB_MODE == "memory":
        print("DB_MODE=memory: demo data would vanish when this script ends. Set DB_MODE=atlas.")
        raise SystemExit(1)
    password = os.getenv("DEMO_USER_PASSWORD")
    generated = not password
    if generated:
        password = secrets.token_urlsafe(9)

    created = run_seed(password)
    if created == 0:
        print("Demo users already exist; nothing added. Run cleanup_demo_data.py --yes first to re-seed.")
    else:
        print(f"\nCreated {created} demo users and {len(PLAN)} submissions (synthetic images).")
        if generated:
            print(f"Demo user password (shown once): {password}")
            print("Set DEMO_USER_PASSWORD in backend/.env before seeding if you want a fixed one.")
    database.close()


if __name__ == "__main__":
    main()
