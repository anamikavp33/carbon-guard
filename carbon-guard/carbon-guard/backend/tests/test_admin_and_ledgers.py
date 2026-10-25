from bson import ObjectId
import database
from repositories import ledger, users
from services import credits, trust
from tests.conftest import submit, submit_ok


def flagged(client, user, user2):
    """Make a submission by user2 that lands in manual review (exact duplicate image)."""
    submit(client, user, seed=50, lat=10, lng=76)
    return submit(client, user2, seed=50, lat=30, lng=50).json()["id"]


def uid(client, headers):
    return client.get("/auth/me", headers=headers).json()["id"]


def test_admin_approve_awards_credits_once(client, user, admin, good_ai):
    sid = submit(client, user, seed=1, scale=5).json()["id"]
    queue = client.get("/admin/submissions?status=pending", headers=admin).json()
    assert [q["id"] for q in queue["items"]] == [sid]
    r = client.post(f"/admin/submissions/{sid}/approve", headers=admin, json={"notes": "Photo and location look right."})
    body = r.json()
    assert r.status_code == 200 and body["status"] == "verified" and body["green_credits_awarded"] == 15.0  # 3*1*5
    assert body["environmental_impact"]["co2_estimate"] == 12.5 and body["reviewed_by"] == "admin@test.com"
    assert body["review_notes"] == "Photo and location look right."
    assert client.post(f"/admin/submissions/{sid}/approve", headers=admin).status_code == 409   # already verified
    me = client.get("/users/me", headers=user).json()
    assert me["green_credits_total"] == 15.0 and me["trust_score"] == 55 and me["total_co2_estimate"] == 12.5
    hist = client.get("/users/me/credit-history", headers=user).json()
    assert hist["green_credits_total"] == 15.0 and [t["amount"] for t in hist["transactions"]] == [15.0]
    assert client.get(f"/submissions/{sid}", headers=user).json()["review_notes"] == "Photo and location look right."


def test_credits_and_trust_are_idempotent_at_service_level(client, user, admin, good_ai):
    sid = submit(client, user, seed=51).json()["id"]
    client.post(f"/admin/submissions/{sid}/approve", headers=admin)
    u = users.get_by_email("asha@example.com")
    from repositories import submissions
    assert credits.award_credits(u["id"], submissions.get(sid)) == 0.0
    assert trust.apply_event(u["id"], sid, "verified_submission", 0) == 0.0
    fresh = users.get_by_email("asha@example.com")
    assert fresh["green_credits_total"] == 15.0 and fresh["trust_score"] == 55


def test_reject_flagged_submission_is_fraud_confirmed(client, user, user2, admin):
    sid = flagged(client, user, user2)
    assert client.post(f"/admin/submissions/{sid}/reject", headers=admin).json()["status"] == "rejected"
    ben = client.get("/users/me/trust-history", headers=user2).json()
    assert ben["trust_score"] == 35 and ben["events"][-1]["event_type"] == "fraud_confirmed"
    assert ben["events"][-1]["score_delta"] == -15 and ben["events"][-1]["reason"]


def test_reject_unflagged_uses_normal_penalty(client, user, admin, good_ai):
    sid = submit(client, user, seed=52).json()["id"]
    assert client.post(f"/admin/submissions/{sid}/reject", headers=admin).status_code == 200
    hist = client.get("/users/me/trust-history", headers=user).json()
    assert hist["trust_score"] == 40 and hist["events"][-1]["event_type"] == "rejected_submission"


def test_reopen_refunds_exactly_and_each_round_counts(client, user, user2, admin):
    sid = flagged(client, user, user2)
    client.post(f"/admin/submissions/{sid}/reject", headers=admin)                      # -15 -> 35
    r = client.post(f"/admin/submissions/{sid}/manual-review", headers=admin).json()     # refund -> 50
    assert r["status"] == "manual_review" and r["review_round"] == 1
    assert client.get("/users/me", headers=user2).json()["trust_score"] == 50
    client.post(f"/admin/submissions/{sid}/reject", headers=admin)                      # round 1: -15 -> 35
    assert client.get("/users/me", headers=user2).json()["trust_score"] == 35
    client.post(f"/admin/submissions/{sid}/manual-review", headers=admin)                # refund -> 50
    client.post(f"/admin/submissions/{sid}/approve", headers=admin)                     # +5 -> 55
    assert client.get("/users/me", headers=user2).json()["trust_score"] == 55
    types = [e["event_type"] for e in client.get("/users/me/trust-history", headers=user2).json()["events"]]
    assert types == ["fraud_confirmed", "review_reopened", "fraud_confirmed", "review_reopened", "verified_submission"]


def test_reopening_auto_rejected_submission_refunds_nothing(client, user, admin):
    sid = submit(client, user, seed=53, lat=0, lng=0).json()["id"]
    assert client.post(f"/admin/submissions/{sid}/approve", headers=admin).status_code == 409   # must reopen first
    assert client.post(f"/admin/submissions/{sid}/manual-review", headers=admin).status_code == 200
    assert client.get("/users/me", headers=user).json()["trust_score"] == 50


def test_pending_can_be_sent_to_manual_review(client, user, admin, good_ai):
    sid = submit(client, user, seed=54).json()["id"]
    r = client.post(f"/admin/submissions/{sid}/manual-review", headers=admin, json={"notes": "Check the roof."})
    assert r.json()["status"] == "manual_review" and r.json()["review_round"] == 0
    assert client.get("/users/me", headers=user).json()["trust_score"] == 50


def test_processing_and_unknown_submissions_cannot_be_reviewed(client, user, admin):
    from repositories import submissions
    sid = submit(client, user, seed=55).json()["id"]
    submissions.update(sid, {"status": "processing"})
    assert client.post(f"/admin/submissions/{sid}/approve", headers=admin).status_code == 409
    assert client.post(f"/admin/submissions/{ObjectId()}/approve", headers=admin).status_code == 404
    assert client.post("/admin/submissions/bad-id/reject", headers=admin).status_code == 404


def test_trust_score_stays_within_bounds(client, user):
    u = users.get_by_email("asha@example.com")
    users.set_trust_score(u["id"], 98.0)
    assert trust.apply_event(u["id"], str(ObjectId()), "verified_submission") == 2.0     # capped at 100
    users.set_trust_score(u["id"], 5.0)
    assert trust.apply_event(u["id"], str(ObjectId()), "rejected_submission") == -5.0    # floored at 0
    assert users.get_by_email("asha@example.com")["trust_score"] == 0.0


def test_credit_rules_change_behaviour_and_are_audited(client, user, admin, good_ai):
    r = client.put("/admin/credit-rules/tree_plantation", headers=admin,
                   json={"base_credit_value": 10, "impact_multiplier": 2})
    assert r.status_code == 200 and r.json()["updated_by"] == "admin@test.com"
    sid = submit(client, user, seed=56, scale=1).json()["id"]
    assert client.post(f"/admin/submissions/{sid}/approve", headers=admin).json()["green_credits_awarded"] == 20.0
    client.put("/admin/credit-rules/tree_plantation", headers=admin,
               json={"base_credit_value": 10, "impact_multiplier": 2, "is_active": False})
    sid2 = submit(client, user, seed=57, scale=1, lat=20).json()["id"]
    assert client.post(f"/admin/submissions/{sid2}/approve", headers=admin).json()["green_credits_awarded"] == 0.0
    actions = [a["action"] for a in client.get("/admin/audit-logs", headers=admin).json()["items"]]
    assert actions.count("credit_rule_updated") == 2 and actions.count("submission_approved") == 2


def test_config_changes_and_validation(client, user, admin, good_ai):
    assert client.put("/admin/config", headers=admin, json={"recommend_threshold": 95}).status_code == 200
    assert submit_ok(client, user, seed=58)["status"] == "manual_review"     # 84 < 95
    assert client.put("/admin/config", headers=admin, json={"trust_rules": {"made_up": 1}}).status_code == 400
    assert client.put("/admin/config", headers=admin, json={"recommend_threshold": 150}).status_code == 422
    assert client.put("/admin/config", headers=user, json={"recommend_threshold": 90}).status_code == 403
    assert client.put("/admin/credit-rules/mining", headers=admin,
                      json={"base_credit_value": 1, "impact_multiplier": 1}).status_code == 404


def test_stats_reports_fraud_flags(client, user, user2, admin, good_ai):
    sid = flagged(client, user, user2)
    first = client.get("/submissions/me", headers=user).json()["items"][0]["id"]
    client.post(f"/admin/submissions/{first}/approve", headers=admin)
    s = client.get("/admin/stats", headers=admin).json()
    assert s["total_users"] == 2 and s["total_submissions"] == 2 and s["fraud_flagged"] == 1
    assert s["by_status"]["manual_review"] == 1 and s["by_status"]["verified"] == 1
    assert s["awaiting_review"] == 1 and s["total_credits_issued"] == 15.0 and s["total_co2_estimate"] == 12.5
    rep = client.get("/admin/reports", headers=admin).json()
    tree = next(a for a in rep["by_activity"] if a["activity_type"] == "tree_plantation")
    assert tree["submitted"] == 2 and tree["verified"] == 1 and tree["credits_issued"] == 15.0
    assert rep["by_month"][0]["submitted"] == 2 and "not certified" in rep["note"]
    flags = client.get("/admin/fraud-flags", headers=admin).json()
    assert flags["total"] == 1 and flags["items"][0]["submission_id"] == sid
    assert flags["items"][0]["related_submission_ids"] == [first]
    detail = client.get(f"/admin/submissions/{sid}", headers=admin).json()
    assert detail["related_submission_ids"] == [first] and detail["user_name"] == "Ben"


def test_admin_user_search_and_detail(client, user, user2, admin, good_ai):
    sid = submit(client, user, seed=60).json()["id"]
    client.post(f"/admin/submissions/{sid}/approve", headers=admin)
    found = client.get("/admin/users?search=ASHA", headers=admin).json()
    assert found["total"] == 1 and found["items"][0]["email"] == "asha@example.com"
    assert client.get("/admin/users?search=.*", headers=admin).json()["total"] == 0     # not a regex
    d = client.get(f"/admin/users/{uid(client, user)}", headers=admin).json()
    assert d["submission_counts"]["verified"] == 1 and len(d["recent_submissions"]) == 1
    assert d["trust_events"][0]["event_type"] == "verified_submission" and d["credit_transactions"][0]["amount"] == 15
    assert client.get(f"/admin/users/{ObjectId()}", headers=admin).status_code == 404
    me = uid(client, admin)
    assert client.patch(f"/admin/users/{me}", headers=admin, json={"is_active": False}).status_code == 400


def test_admin_submission_filters(client, user, user2, admin):
    submit(client, user, seed=61, activity="solar_panel", lat=10)
    submit(client, user2, seed=62, activity="tree_plantation", lat=20)
    assert client.get("/admin/submissions?activity_type=solar_panel", headers=admin).json()["total"] == 1
    assert client.get("/admin/submissions?search=ben@", headers=admin).json()["total"] == 1
    assert client.get("/admin/submissions?status=bogus", headers=admin).status_code == 422


def test_ledger_unique_index_blocks_double_award(client):
    db = database.get_db()
    a, b = ObjectId(), ObjectId()
    assert ledger.add_credit_transaction(a, b, 5.0, {}) is True
    assert ledger.add_credit_transaction(a, b, 5.0, {}) is False
    assert db.credit_transactions.count_documents({}) == 1
