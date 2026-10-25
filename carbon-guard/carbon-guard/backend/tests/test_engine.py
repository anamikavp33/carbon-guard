from repositories.config_store import DEFAULT_CONFIG as CFG
from services import image_utils, verification_engine as eng

LOC = {"gps_valid": True, "accuracy_ok": True}
BAD_LOC = {"gps_valid": False, "accuracy_ok": None}
NO_SAT = {"status": "not_configured", "supports_claim": None}
SAT_YES = {"status": "available", "supports_claim": True}
NO_FRAUD = {"flags": []}


def ai(conf, matched=True, status="available"):
    return {"status": status, "confidence": conf, "matched": matched}


def test_score_and_recommendation():
    assert eng.decide(ai(0.9), LOC, NO_SAT, NO_FRAUD, CFG)["status"] == "pending"          # 54+15+0+15 = 84
    assert eng.decide(ai(0.9), LOC, SAT_YES, NO_FRAUD, CFG)["score"] == 94.0
    assert eng.decide(ai(0.6), LOC, NO_SAT, NO_FRAUD, CFG)["status"] == "manual_review"    # 36+30 = 66
    assert eng.decide(ai(0.9, matched=False), LOC, NO_SAT, NO_FRAUD, CFG)["status"] == "manual_review"


def test_missing_evidence_earns_nothing():
    d = eng.decide({"status": "unavailable", "confidence": None, "matched": None}, LOC, NO_SAT, NO_FRAUD, CFG)
    assert d["components"]["ai"] == 0 and d["components"]["satellite"] == 0 and d["status"] == "manual_review"


def test_engine_never_verifies_automatically():
    best = eng.decide(ai(1.0), LOC, SAT_YES, NO_FRAUD, CFG)
    assert best["score"] == 100 and best["status"] == "pending"


def test_gps_invalid_rejected_and_fraud_forces_review():
    assert eng.decide(ai(0.95), BAD_LOC, NO_SAT, NO_FRAUD, CFG)["status"] == "rejected"
    assert eng.decide(ai(0.95), LOC, SAT_YES, {"flags": ["duplicate_location"]}, CFG)["status"] == "manual_review"


def test_every_decision_is_explained():
    d = eng.decide(ai(0.9), LOC, NO_SAT, NO_FRAUD, CFG)
    assert d["reasons"][-1].startswith("Result:") and set(d["components"]) == {"ai", "gps", "satellite", "fraud"}


def test_dhash_distance_properties():
    from tests.conftest import make_image_bytes
    from PIL import Image
    import io
    h = lambda raw: image_utils.dhash(Image.open(io.BytesIO(raw)))
    same = image_utils.hamming(h(make_image_bytes(1)), h(make_image_bytes(1, size=100, fmt="JPEG", quality=60)))
    diff = image_utils.hamming(h(make_image_bytes(1)), h(make_image_bytes(2)))
    assert same <= 8 < diff
