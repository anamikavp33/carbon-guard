"""Test setup: uses the in-memory database (mongomock) and a temporary upload folder.
Nothing here touches MongoDB Atlas, Nominatim or Copernicus. Atlas itself is checked with
scripts/check_db.py."""
import io
import os
import random
import tempfile

_tmp = tempfile.mkdtemp(prefix="cg_uploads_")
os.environ.update({
    "DB_MODE": "memory", "JWT_SECRET_KEY": "test-secret-key-for-pytest-only",
    "ADMIN_EMAIL": "admin@test.com", "ADMIN_PASSWORD": "AdminPass123",
    "UPLOAD_DIR": _tmp, "GEOCODING_ENABLED": "false", "SATELLITE_PROVIDER": "none",
    "AI_MODEL_PATH": os.path.join(_tmp, "no-model-here.onnx"), "AUTH_RATE_LIMIT_PER_MINUTE": "1000",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from main import app  # noqa: E402
from services import ai_verification, rate_limit  # noqa: E402

UPLOAD_DIR = _tmp


def make_image_bytes(seed: int, size: int = 256, fmt: str = "PNG", quality: int = 90) -> bytes:
    """A random 16x16 block pattern. Different seeds look different; same seed looks the same."""
    rng = random.Random(seed)
    small = Image.new("L", (16, 16))
    small.putdata([rng.randint(0, 255) for _ in range(256)])
    img = small.resize((size, size), Image.NEAREST).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format=fmt, **({"quality": quality} if fmt == "JPEG" else {}))
    return buf.getvalue()


def matched_ai(confidence=0.9):
    def fake(image_path, activity_type, min_confidence=0.6):
        return {"status": "available", "model": "test-model", "predicted_class": activity_type,
                "confidence": confidence, "matched": confidence >= min_confidence,
                "scores": {activity_type: confidence}, "warnings": []}
    return fake


@pytest.fixture
def client():
    ai_verification.reset()
    rate_limit.reset()
    with TestClient(app) as c:
        yield c


@pytest.fixture
def good_ai(monkeypatch):
    """Pretend a trained model is installed and confidently agrees with every claim."""
    monkeypatch.setattr(ai_verification, "run_ai_verification", matched_ai(0.9))


def register_login(client, email="asha@example.com", password="test12345", name="Asha"):
    client.post("/auth/register", json={"name": name, "email": email, "password": password})
    token = client.post("/auth/login", json={"email": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def user(client):
    return register_login(client)


@pytest.fixture
def user2(client):
    return register_login(client, email="ben@example.com", name="Ben")


@pytest.fixture
def admin(client):
    r = client.post("/auth/login", json={"email": "admin@test.com", "password": "AdminPass123"})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def submit(client, headers, seed=1, lat=10.0, lng=76.0, activity="tree_plantation", scale=5,
           accuracy=10.0, image=None, filename="photo.png", **extra):
    """POST /submissions as a multipart form, like the Flutter app does."""
    data = {"activity_type": activity, "latitude": str(lat), "longitude": str(lng),
            "scale_value": str(scale), "description": "test", **extra}
    if accuracy is not None:
        data["gps_accuracy_m"] = str(accuracy)
    raw = image if image is not None else make_image_bytes(seed)
    return client.post("/submissions", data=data, files={"image": (filename, raw, "image/png")}, headers=headers)


def submit_ok(client, headers, **kw) -> dict:
    """Submit and return the processed submission detail (background checks already ran)."""
    r = submit(client, headers, **kw)
    assert r.status_code == 201, r.text
    return client.get(f"/submissions/{r.json()['id']}", headers=headers).json()
