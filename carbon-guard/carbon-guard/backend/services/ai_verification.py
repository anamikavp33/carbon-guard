"""AI image verification with a MobileNetV2 image classifier exported to ONNX.

How it works:
  1. The model file (default ../ai_model/weights/carbon_guard_mobilenetv2.onnx) and its
     labels file (same name + ".labels.json") are loaded once, the first time they are needed.
  2. The image is resized to 224x224 and scaled to [-1, 1] (MobileNetV2 preprocessing).
  3. The model returns one probability per class; the highest one is the prediction.

If the model file or onnxruntime is missing, the result has status "unavailable" and
earns no points. Nothing is guessed or simulated.

The AI output is ONE evidence signal. Recognising a tree or a solar panel in a photo does
not prove that the claimed activity happened, is new, or qualifies for credits.
How to train and evaluate the model: ai_model/README.md.
"""
import json
import logging
import os
import threading

from config import settings

log = logging.getLogger("carbon_guard")
INPUT_SIZE = 224
ACTIVITY_CLASSES = ("tree_plantation", "solar_panel", "water_harvesting")

_lock = threading.Lock()
_model = None          # (session, input_name, labels) once loaded
_load_error = None     # why the model could not be loaded (shown to admins)


def labels_path(model_path: str) -> str:
    return model_path + ".labels.json"


def reset():
    """Forget the loaded model (used by tests and after replacing the model file)."""
    global _model, _load_error
    with _lock:
        _model, _load_error = None, None


def _load():
    global _model, _load_error
    with _lock:
        if _model is not None or _load_error is not None:
            return
        path = os.path.abspath(settings.AI_MODEL_PATH)
        if not os.path.isfile(path):
            _load_error = "No AI model file installed (see ai_model/README.md)."
            return
        try:
            import onnxruntime as ort
            with open(labels_path(path), encoding="utf-8") as f:
                labels = json.load(f)
            session = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
            _model = (session, session.get_inputs()[0].name, labels)
            log.info("AI model loaded: %s (%d classes)", path, len(labels))
        except Exception as e:   # missing package, broken file, missing labels...
            _load_error = f"AI model could not be loaded: {type(e).__name__}"
            log.exception("AI model could not be loaded")


def preprocess(image_path: str):
    """Image file -> float32 array of shape (1, 224, 224, 3) with values in [-1, 1]."""
    import numpy as np
    from PIL import Image
    img = Image.open(image_path).convert("RGB").resize((INPUT_SIZE, INPUT_SIZE), Image.BILINEAR)
    arr = np.asarray(img, dtype=np.float32) / 127.5 - 1.0
    return arr[np.newaxis, ...]


def model_status() -> dict:
    _load()
    return {"available": _model is not None, "detail": _load_error or "AI model loaded."}


def run_ai_verification(image_path: str, activity_type: str, min_confidence: float = 0.6) -> dict:
    _load()
    if _model is None:
        return {
            "status": "unavailable", "model": None, "predicted_class": None, "confidence": None,
            "matched": None, "scores": {}, "warnings": [_load_error],
        }
    import numpy as np
    session, input_name, labels = _model
    try:
        probs = np.asarray(session.run(None, {input_name: preprocess(image_path)})[0][0], dtype=np.float64)
    except Exception as e:
        log.exception("AI inference failed")
        return {
            "status": "error", "model": os.path.basename(settings.AI_MODEL_PATH), "predicted_class": None,
            "confidence": None, "matched": None, "scores": {},
            "warnings": [f"AI check failed ({type(e).__name__}); a human must review the image."],
        }
    if probs.min() < 0 or abs(probs.sum() - 1.0) > 0.01:     # model returned raw scores: apply softmax
        e = np.exp(probs - probs.max())
        probs = e / e.sum()
    best = int(probs.argmax())
    predicted, confidence = labels[best], round(float(probs[best]), 4)
    matched = predicted == activity_type and confidence >= min_confidence
    warnings = []
    if predicted == activity_type and not matched:
        warnings.append(f"Confidence {confidence} is below the required {min_confidence}.")
    return {
        "status": "available",
        "model": os.path.basename(settings.AI_MODEL_PATH),
        "predicted_class": predicted,
        "confidence": confidence,
        "matched": matched,
        "scores": {label: round(float(p), 4) for label, p in zip(labels, probs)},
        "warnings": warnings,
    }
