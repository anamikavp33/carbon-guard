"""AI inference code with a tiny hand-made ONNX model, and the satellite / geocoding modules with
the internet replaced by fakes. These prove the CODE works; they say nothing about the accuracy
of a real trained model or the live Copernicus / Nominatim services."""
import io
import json
import os

import pytest
from PIL import Image

from config import settings
from repositories.config_store import DEFAULT_CONFIG as CFG
from services import ai_verification, geocoding, http_client, satellite
from tests.conftest import UPLOAD_DIR

LABELS = ["other", "solar_panel", "tree_plantation", "water_harvesting"]


def build_tiny_model(path: str):
    """Average colour -> 4 class scores. Blue -> solar, green -> tree, red -> water. NOT a real model."""
    onnx = pytest.importorskip("onnx")
    from onnx import TensorProto, helper
    import numpy as np
    w = np.array([[0, 0, 0, 5], [0, 0, 5, 0], [0, 5, 0, 0]], dtype=np.float32)   # rows: R, G, B
    graph = helper.make_graph(
        [helper.make_node("ReduceMean", ["input"], ["mean"], axes=[1, 2], keepdims=0),
         helper.make_node("MatMul", ["mean", "W"], ["logits"]),
         helper.make_node("Softmax", ["logits"], ["probs"], axis=1)],
        "tiny",
        [helper.make_tensor_value_info("input", TensorProto.FLOAT, [1, 224, 224, 3])],
        [helper.make_tensor_value_info("probs", TensorProto.FLOAT, [1, 4])],
        [helper.make_tensor("W", TensorProto.FLOAT, [3, 4], w.flatten().tolist())],
    )
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 13)])
    model.ir_version = 8
    onnx.save(model, path)
    with open(ai_verification.labels_path(path), "w") as f:
        json.dump(LABELS, f)


def solid_image(color) -> str:
    path = os.path.join(UPLOAD_DIR, f"solid_{'_'.join(map(str, color))}.png")
    Image.new("RGB", (300, 200), color).save(path)
    return path


@pytest.fixture
def tiny_model(monkeypatch):
    path = os.path.join(UPLOAD_DIR, "tiny.onnx")
    build_tiny_model(path)
    monkeypatch.setattr(settings, "AI_MODEL_PATH", path)
    ai_verification.reset()
    yield path
    ai_verification.reset()


def test_onnx_model_inference(tiny_model):
    green = ai_verification.run_ai_verification(solid_image((0, 255, 0)), "tree_plantation", 0.6)
    assert green["status"] == "available" and green["predicted_class"] == "tree_plantation"
    assert green["matched"] is True and green["confidence"] > 0.9 and set(green["scores"]) == set(LABELS)
    blue = ai_verification.run_ai_verification(solid_image((0, 0, 255)), "tree_plantation", 0.6)
    assert blue["predicted_class"] == "solar_panel" and blue["matched"] is False


def test_model_through_the_api(client, user, tiny_model):
    from tests.conftest import submit_ok
    buf = io.BytesIO()
    Image.new("RGB", (256, 256), (0, 200, 0)).save(buf, format="PNG")
    d = submit_ok(client, user, image=buf.getvalue())
    assert d["ai_verification"]["status"] == "available" and d["ai_verification"]["predicted_class"] == "tree_plantation"
    assert d["status"] == "pending"


def test_missing_or_broken_model_is_unavailable(monkeypatch):
    monkeypatch.setattr(settings, "AI_MODEL_PATH", os.path.join(UPLOAD_DIR, "missing.onnx"))
    ai_verification.reset()
    r = ai_verification.run_ai_verification(solid_image((1, 2, 3)), "tree_plantation")
    assert r["status"] == "unavailable" and r["confidence"] is None and "No AI model" in r["warnings"][0]
    broken = os.path.join(UPLOAD_DIR, "broken.onnx")
    with open(broken, "wb") as f:
        f.write(b"not a model")
    monkeypatch.setattr(settings, "AI_MODEL_PATH", broken)
    ai_verification.reset()
    assert ai_verification.run_ai_verification(solid_image((1, 2, 3)), "tree_plantation")["status"] == "unavailable"
    ai_verification.reset()


# ---------------- satellite ----------------
def png_bytes(mode, size, color) -> bytes:
    buf = io.BytesIO()
    Image.new(mode, size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_ndvi_mean_ignores_pixels_without_data():
    img = Image.new("LA", (2, 1))
    img.putdata([(191, 255), (0, 0)])          # 191 -> NDVI ~0.5 ; second pixel has no data
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    assert satellite.ndvi_mean_from_png(buf.getvalue()) == pytest.approx(0.498, abs=0.01)
    assert satellite.ndvi_mean_from_png(png_bytes("LA", (2, 2), (100, 0))) is None


def test_satellite_not_configured(client):
    assert satellite.run_satellite_verification("x", 10, 76, "tree_plantation", CFG)["status"] == "not_configured"


@pytest.fixture
def copernicus(monkeypatch):
    monkeypatch.setattr(settings, "SATELLITE_PROVIDER", "copernicus")
    monkeypatch.setattr(satellite, "_token", {"value": None, "expires": 0.0})
    calls = []

    def fake_json(url, data=None, headers=None, method=None):
        calls.append(url)
        if url == satellite.TOKEN_URL:
            return {"access_token": "tok", "expires_in": 600}
        return {"features": [{"properties": {"datetime": "2026-09-01T05:00:00Z", "eo:cloud_cover": 20}},
                             {"properties": {"datetime": "2026-10-10T05:00:00Z", "eo:cloud_cover": 5.5}}]}

    def fake_bytes(url, data=None, headers=None, method=None):
        body = json.loads(data)
        assert headers["Authorization"] == "Bearer tok"
        assert body["input"]["data"][0]["dataFilter"]["timeRange"]["from"] == "2026-10-10T00:00:00Z"
        if "NDVI" in body["evalscript"] or "B08" in body["evalscript"]:
            return png_bytes("LA", (4, 4), (204, 255))        # NDVI ~0.6
        return png_bytes("RGB", (8, 8), (20, 120, 20))

    monkeypatch.setattr(http_client, "request_json", fake_json)
    monkeypatch.setattr(http_client, "request_bytes", fake_bytes)
    return calls


def test_satellite_copernicus_flow(client, copernicus):
    r = satellite.run_satellite_verification("abc123", 10, 76, "tree_plantation", CFG)
    assert r["status"] == "available" and r["acquisition_date"] == "2026-10-10" and r["cloud_cover"] == 5.5
    assert r["ndvi_mean"] == pytest.approx(0.6, abs=0.01) and r["supports_claim"] is True
    assert r["image_url"] == "/uploads/satellite/abc123.png"
    assert os.path.isfile(os.path.join(UPLOAD_DIR, "satellite", "abc123.png"))
    solar = satellite.run_satellite_verification("abc124", 10, 76, "solar_panel", CFG)
    assert solar["supports_claim"] is None and solar["ndvi_mean"] is None
    assert copernicus.count(satellite.TOKEN_URL) == 1        # token is reused


def test_satellite_points_reach_the_score(client, user, copernicus, good_ai):
    from tests.conftest import submit_ok
    d = submit_ok(client, user)
    assert d["satellite_verification"]["status"] == "available" and d["score_components"]["satellite"] == 10


def test_satellite_failure_is_reported_not_penalised(client, monkeypatch):
    monkeypatch.setattr(settings, "SATELLITE_PROVIDER", "copernicus")
    monkeypatch.setattr(satellite, "_token", {"value": None, "expires": 0.0})

    def down(*a, **k):
        raise OSError("network down")
    monkeypatch.setattr(http_client, "request_json", down)
    r = satellite.run_satellite_verification("x", 10, 76, "tree_plantation", CFG)
    assert r["status"] == "error" and "No penalty" in r["notes"][0]


def test_satellite_no_recent_image(client, monkeypatch):
    monkeypatch.setattr(settings, "SATELLITE_PROVIDER", "copernicus")
    monkeypatch.setattr(satellite, "_token", {"value": "tok", "expires": 9e18})
    monkeypatch.setattr(http_client, "request_json", lambda *a, **k: {"features": []})
    assert satellite.run_satellite_verification("x", 10, 76, "tree_plantation", CFG)["status"] == "no_recent_image"


# ---------------- reverse geocoding ----------------
def test_geocoding_disabled_ok_cached_and_unavailable(client, monkeypatch):
    assert geocoding.reverse_geocode(10, 76)["status"] == "disabled"
    monkeypatch.setattr(settings, "GEOCODING_ENABLED", True)
    monkeypatch.setattr(geocoding, "_last_call", 0.0)
    calls = []

    def fake(url, data=None, headers=None, method=None):
        calls.append(headers["User-Agent"])
        return {"display_name": "Kochi, Kerala, India"}
    monkeypatch.setattr(http_client, "request_json", fake)
    assert geocoding.reverse_geocode(9.93121, 76.26731) == {"status": "ok", "address": "Kochi, Kerala, India"}
    assert geocoding.reverse_geocode(9.93119, 76.26729)["address"] == "Kochi, Kerala, India"   # cached
    assert len(calls) == 1 and calls[0].startswith("CarbonGuard")

    def down(*a, **k):
        raise TimeoutError()
    monkeypatch.setattr(http_client, "request_json", down)
    assert geocoding.reverse_geocode(20, 20) == {"status": "unavailable", "address": None}
