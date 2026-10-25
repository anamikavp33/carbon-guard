"""The database scripts in carbon-guard/database: seed, integrity check, cleanup (in-memory DB)."""
import importlib.util
import os

import database
from config import settings
from repositories import users

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load(rel_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, rel_path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


seed = load("database/seed/seed_demo_data.py", "seed_demo_data")
cleanup = load("database/seed/cleanup_demo_data.py", "cleanup_demo_data")
integrity = load("database/scripts/check_integrity.py", "check_integrity")


def test_seed_creates_consistent_demo_data_once(client):
    assert seed.run_seed("demo-password-1") == 3
    db = database.get_db()
    assert db.users.count_documents({"is_demo": True}) == 3
    statuses = {s["status"] for s in db.submissions.find()}
    assert {"verified", "rejected", "manual_review"} <= statuses
    assert db.fraud_logs.count_documents({}) >= 1 and db.audit_logs.count_documents({}) == 4
    assert integrity.check(db, settings.UPLOAD_DIR) == []
    assert seed.run_seed("demo-password-1") == 0          # second run adds nothing
    assert db.submissions.count_documents({}) == len(seed.PLAN)


def test_demo_user_can_log_in(client):
    seed.run_seed("demo-password-1")
    r = client.post("/auth/login", json={"email": "demo.asha@example.com", "password": "demo-password-1"})
    assert r.status_code == 200


def test_integrity_check_finds_problems(client):
    seed.run_seed("demo-password-1")
    db = database.get_db()
    asha = users.get_by_email("demo.asha@example.com")
    db.users.update_one({"email": "demo.asha@example.com"}, {"$inc": {"green_credits_total": 5, "trust_score": 3}})
    verified = db.submissions.find_one({"status": "verified"})
    db.credit_transactions.delete_many({"submission_id": verified["_id"]})
    problems = integrity.check(db, settings.UPLOAD_DIR)
    assert any("green_credits_total" in p for p in problems)
    assert any("trust_score" in p and asha["email"] in p for p in problems)
    assert any("verified but has 0 credit award" in p for p in problems)


def test_cleanup_dry_run_then_delete_keeps_real_users(client, user):
    seed.run_seed("demo-password-1")
    db = database.get_db()
    dry = cleanup.cleanup(db, settings.UPLOAD_DIR, include_smoke=False, really=False)
    assert dry["users"] == 3 and dry["submissions"] == len(seed.PLAN)
    assert db.users.count_documents({"is_demo": True}) == 3            # nothing deleted yet
    cleanup.cleanup(db, settings.UPLOAD_DIR, include_smoke=False, really=True)
    assert db.users.count_documents({"is_demo": True}) == 0
    assert db.submissions.count_documents({}) == 0 and db.credit_transactions.count_documents({}) == 0
    assert users.get_by_email("asha@example.com") is not None           # a real user survives
    assert users.get_by_email(settings.ADMIN_EMAIL) is not None
    assert integrity.check(db, settings.UPLOAD_DIR) == []
