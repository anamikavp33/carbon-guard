from datetime import datetime, timedelta, timezone
import jwt
from config import settings
from tests.conftest import register_login


def test_health(client):
    h = client.get("/health").json()
    assert h["database"] == "connected" and h["ai_model"] == "unavailable" and h["satellite"] == "none"


def test_register_login_me(client):
    r = client.post("/auth/register", json={"name": " Asha ", "email": "Asha@Example.com", "password": "test12345"})
    assert r.status_code == 201 and r.json()["name"] == "Asha" and r.json()["email"] == "asha@example.com"
    login = client.post("/auth/login", json={"email": "asha@example.com", "password": "test12345"}).json()
    assert login["token_type"] == "bearer" and login["expires_in"] == settings.JWT_EXPIRE_MINUTES * 60
    me = client.get("/auth/me", headers={"Authorization": "Bearer " + login["access_token"]}).json()
    assert me["email"] == "asha@example.com" and me["role"] == "user"
    assert "password" not in str(me)


def test_new_user_profile_defaults(client, user):
    p = client.get("/users/me", headers=user).json()
    assert p["trust_score"] == 50 and p["green_credits_total"] == 0 and p["is_active"] is True
    assert p["submission_counts"]["total"] == 0 and p["created_at"].endswith("Z")
    assert "password_hash" not in p


def test_duplicate_email_rejected_case_insensitive(client):
    client.post("/auth/register", json={"name": "A", "email": "a@x.com", "password": "password1"})
    r = client.post("/auth/register", json={"name": "B", "email": "A@X.com", "password": "password1"})
    assert r.status_code == 400


def test_wrong_password_and_validation(client):
    client.post("/auth/register", json={"name": "A", "email": "a@x.com", "password": "password1"})
    assert client.post("/auth/login", json={"email": "a@x.com", "password": "nope"}).status_code == 401
    assert client.post("/auth/login", json={"email": "nobody@x.com", "password": "password1"}).status_code == 401
    short = client.post("/auth/register", json={"name": "A", "email": "z@x.com", "password": "Qz7"})
    assert short.status_code == 422 and short.json()["detail"][0]["loc"] == ["body", "password"]
    assert "Qz7" not in short.text              # submitted values are never echoed back
    assert client.post("/auth/register", json={"name": "   ", "email": "y@x.com", "password": "password1"}).status_code == 422
    assert client.post("/auth/register", json={"name": "A", "email": "not-an-email", "password": "password1"}).status_code == 422


def test_password_is_hashed_in_db(client):
    client.post("/auth/register", json={"name": "A", "email": "a@x.com", "password": "password1"})
    import database
    doc = database.get_db().users.find_one({"email": "a@x.com"})
    assert doc["password_hash"].startswith("$2") and doc["password_hash"] != "password1"


def test_endpoints_need_valid_token(client, user):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401
    uid = client.get("/auth/me", headers=user).json()["id"]
    expired = jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) - timedelta(minutes=1)},
                         settings.JWT_SECRET_KEY, algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401
    forged = jwt.encode({"sub": uid, "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
                        "wrong-secret", algorithm="HS256")
    assert client.get("/auth/me", headers={"Authorization": f"Bearer {forged}"}).status_code == 401


def test_user_cannot_use_admin_routes_but_admin_can(client, user, admin):
    for path in ("/admin/stats", "/admin/submissions", "/admin/users", "/admin/reports",
                 "/admin/fraud-flags", "/admin/credit-rules", "/admin/config", "/admin/audit-logs"):
        assert client.get(path, headers=user).status_code == 403, path
        assert client.get(path, headers=admin).status_code == 200, path


def test_cannot_self_register_as_admin(client):
    r = client.post("/auth/register", json={"name": "X", "email": "x@x.com", "password": "password1", "role": "admin"})
    assert r.json()["role"] == "user"


def test_deactivated_user_is_locked_out(client, user, admin):
    uid = client.get("/auth/me", headers=user).json()["id"]
    assert client.patch(f"/admin/users/{uid}", headers=admin, json={"is_active": False}).json()["is_active"] is False
    assert client.get("/auth/me", headers=user).status_code == 403
    assert client.post("/auth/login", json={"email": "asha@example.com", "password": "test12345"}).status_code == 403
    client.patch(f"/admin/users/{uid}", headers=admin, json={"is_active": True})
    assert client.get("/auth/me", headers=user).status_code == 200


def test_login_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_PER_MINUTE", 3)
    codes = [client.post("/auth/login", json={"email": "a@x.com", "password": "wrong"}).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_rules_info(client, user):
    r = client.get("/info/rules", headers=user).json()
    assert {a["activity_type"] for a in r["activity_types"]} == {"tree_plantation", "solar_panel", "water_harvesting"}
    assert r["trust"]["initial"] == 50 and r["evidence"]["ai_model_available"] is False
    assert "not legally recognised" in r["disclaimer"]
