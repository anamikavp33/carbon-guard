from tests.conftest import make_image_bytes, matched_ai, submit, submit_ok


def test_without_ai_model_goes_to_manual_review_without_penalty(client, user):
    d = submit_ok(client, user)
    assert d["status"] == "manual_review"
    assert d["ai_verification"]["status"] == "unavailable" and d["ai_verification"]["confidence"] is None
    assert d["satellite_verification"]["status"] == "not_configured"
    assert d["score_components"] == {"ai": 0.0, "gps": 15.0, "satellite": 0.0, "fraud": 15.0}
    assert any("AI model not available" in r for r in d["decision_reasons"])
    assert d["green_credits_awarded"] == 0
    assert client.get("/users/me", headers=user).json()["trust_score"] == 50      # untouched


def test_good_evidence_is_pending_admin_approval_not_auto_verified(client, user, good_ai):
    r = submit(client, user)
    assert r.status_code == 201 and r.json()["status"] == "processing"     # answer before checks run
    sid = r.json()["id"]
    assert client.get(f"/submissions/{sid}/status", headers=user).json()["status"] == "pending"
    d = client.get(f"/submissions/{sid}", headers=user).json()
    assert d["verification_score"] == 84.0         # 0.9*60 + 15 + 0 + 15
    assert d["green_credits_awarded"] == 0 and d["environmental_impact"]["co2_estimate"] is None
    assert d["gps"] == {"lat": 10.0, "lng": 76.0, "accuracy_m": 10.0, "is_mocked": None}
    assert d["created_at"].endswith("Z")
    assert client.get("/users/me", headers=user).json()["green_credits_total"] == 0


def test_gps_accuracy_affects_points(client, user, good_ai):
    unknown = submit_ok(client, user, seed=2, lat=20, accuracy=None)
    poor = submit_ok(client, user, seed=3, lat=30, accuracy=500)
    assert unknown["score_components"]["gps"] == 7.5 and unknown["location_verification"]["accuracy_ok"] is None
    assert poor["score_components"]["gps"] == 0.0 and poor["location_verification"]["accuracy_ok"] is False


def test_uploaded_image_is_retrievable(client, user):
    d = submit_ok(client, user, seed=2)
    got = client.get(d["image_url"])
    assert got.status_code == 200 and got.content == make_image_bytes(2)


def test_invalid_inputs(client, user, monkeypatch):
    assert submit(client, user, image=b"this is text, not an image").status_code == 400
    assert submit(client, user, image=b"").status_code == 400
    assert submit(client, user, activity="mining").status_code == 422
    assert submit(client, user, scale=0).status_code == 422
    assert submit(client, user, lat=200).status_code == 422
    assert submit(client, user, description="x" * 501).status_code == 422
    assert submit(client, {}).status_code == 401
    gif = __import__("io").BytesIO()
    from PIL import Image
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    assert submit(client, user, image=gif.getvalue()).status_code == 400
    from config import settings
    monkeypatch.setattr(settings, "MAX_IMAGE_MB", 0)
    assert "larger than" in submit(client, user).json()["detail"]


def test_users_only_see_own_submissions(client, user, user2, admin):
    sid = submit(client, user, seed=14).json()["id"]
    assert client.get(f"/submissions/{sid}", headers=user2).status_code == 404
    assert client.get(f"/submissions/{sid}/status", headers=user2).status_code == 404
    assert client.get(f"/submissions/{sid}", headers=admin).status_code == 200
    assert client.get("/submissions/me", headers=user2).json()["total"] == 0
    mine = client.get("/submissions/me", headers=user).json()
    assert mine["total"] == 1 and mine["items"][0]["id"] == sid
    assert client.get("/submissions/not-an-id", headers=user).status_code == 404


def test_my_submissions_pagination(client, user):
    for i in range(3):
        submit(client, user, seed=300 + i, lat=10 + i)
    page = client.get("/submissions/me?skip=1&limit=1", headers=user).json()
    assert page["total"] == 3 and len(page["items"]) == 1 and page["skip"] == 1


def test_default_gps_is_rejected_without_penalty(client, user):
    d = submit_ok(client, user, seed=5, lat=0, lng=0)
    assert d["status"] == "rejected" and d["location_verification"]["gps_valid"] is False
    assert d["satellite_verification"]["status"] == "skipped"
    assert client.get("/users/me", headers=user).json()["trust_score"] == 50


def test_exact_duplicate_image_flagged_without_naming_others(client, user, user2, good_ai):
    submit(client, user, seed=6, lat=10, lng=76)
    d = submit_ok(client, user2, seed=6, lat=30, lng=50)
    assert d["status"] == "manual_review" and "duplicate_image" in d["fraud_check"]["flags"]
    assert d["fraud_check"]["reasons"] and "related_submission_ids" not in d["fraud_check"]
    assert client.get("/users/me", headers=user2).json()["trust_score"] == 50   # a flag is not a penalty


def test_visually_similar_image_flagged(client, user):
    submit(client, user, seed=7, lat=10, lng=76)
    d = submit_ok(client, user, image=make_image_bytes(7, size=128, fmt="JPEG", quality=60), lat=40, lng=20)
    assert "similar_image" in d["fraud_check"]["flags"] and "duplicate_image" not in d["fraud_check"]["flags"]


def test_different_images_not_flagged(client, user, good_ai):
    submit(client, user, seed=8, lat=10, lng=76)
    d = submit_ok(client, user, seed=9, lat=40, lng=20)
    assert d["fraud_check"]["flags"] == [] and d["status"] == "pending"


def test_nearby_location_flagged_far_location_not(client, user):
    submit(client, user, seed=10, lat=10.0000, lng=76.0000)
    near = submit_ok(client, user, seed=11, lat=10.0002, lng=76.0000)     # ~22 m
    far = submit_ok(client, user, seed=12, lat=10.0100, lng=76.0000)      # ~1.1 km
    assert "duplicate_location" in near["fraud_check"]["flags"]
    assert "duplicate_location" not in far["fraud_check"]["flags"]


def test_rapid_submissions_flagged(client, user):
    for i in range(5):
        submit(client, user, seed=100 + i, lat=10 + i, lng=76)
    sixth = submit_ok(client, user, seed=200, lat=30, lng=76)
    assert "rapid_submissions" in sixth["fraud_check"]["flags"]


def test_implausible_scale_flagged(client, user):
    d = submit_ok(client, user, seed=13, scale=999999)
    assert "implausible_scale" in d["fraud_check"]["flags"] and d["status"] == "manual_review"


def test_ai_seeing_another_activity_is_flagged(client, user, monkeypatch):
    from services import ai_verification
    monkeypatch.setattr(ai_verification, "run_ai_verification", lambda *a, **k: {
        "status": "available", "model": "t", "predicted_class": "solar_panel", "confidence": 0.95,
        "matched": False, "scores": {}, "warnings": []})
    d = submit_ok(client, user, activity="tree_plantation")
    assert "activity_mismatch" in d["fraud_check"]["flags"] and d["score_components"]["ai"] == 0


def test_processing_crash_keeps_submission_for_manual_review(client, user, monkeypatch):
    from services import fraud_detection

    def boom(*a, **k):
        raise RuntimeError("simulated server bug")
    monkeypatch.setattr(fraud_detection, "run_fraud_detection", boom)
    d = submit_ok(client, user)
    assert d["status"] == "manual_review"
    assert "server problem" in d["decision_reasons"][0]
    assert client.get("/users/me", headers=user).json()["trust_score"] == 50


def test_mock_location_is_flagged(client, user):
    d = submit_ok(client, user, gps_is_mocked="true")
    assert "mock_location" in d["fraud_check"]["flags"] and d["gps"]["is_mocked"] is True
    assert "mock_location" not in submit_ok(client, user, seed=2, lat=30, gps_is_mocked="false")["fraud_check"]["flags"]


def test_low_ai_confidence_goes_to_manual_review(client, user, monkeypatch):
    from services import ai_verification
    monkeypatch.setattr(ai_verification, "run_ai_verification", matched_ai(0.5))
    d = submit_ok(client, user)
    assert d["status"] == "manual_review" and d["score_components"]["ai"] == 0
