"""Measure the installed model on a labelled TEST set, using exactly the backend's inference code.

    cd carbon-guard\\backend
    venv\\Scripts\\activate
    python ..\\ai_model\\evaluation\\evaluate.py --test-dir D:\\carbon_guard_dataset\\test

Test folder layout: test/<class>/*.jpg with class folders other, solar_panel, tree_plantation,
water_harvesting. Use photos the model never saw during training (ideally taken by the team).

Writes results.json and results.md next to this script (or --out). These are the ONLY accuracy numbers
the project should report, together with the test-set size and where the photos came from.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend")))

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".webp")


def evaluate(test_dir: str, min_confidence: float) -> dict:
    from services import ai_verification
    status = ai_verification.model_status()
    if not status["available"]:
        raise SystemExit(f"Model not available: {status['detail']}")
    _, _, labels = ai_verification._model

    confusion = {t: {p: 0 for p in labels} for t in labels}
    claim_ok = claim_total = 0
    for true_label in labels:
        folder = os.path.join(test_dir, true_label)
        if not os.path.isdir(folder):
            continue
        for name in sorted(os.listdir(folder)):
            if not name.lower().endswith(IMAGE_EXT):
                continue
            r = ai_verification.run_ai_verification(os.path.join(folder, name), true_label, min_confidence)
            if r["status"] != "available":
                raise SystemExit(f"Inference failed on {name}: {r['warnings']}")
            confusion[true_label][r["predicted_class"]] += 1
            if true_label != "other":           # how often a TRUE claim is accepted as "matched"
                claim_total += 1
                claim_ok += bool(r["matched"])

    total = sum(sum(row.values()) for row in confusion.values())
    if total == 0:
        raise SystemExit(f"No images found under {test_dir}/<class>/")
    correct = sum(confusion[c][c] for c in labels)
    per_class = {}
    for c in labels:
        tp = confusion[c][c]
        actual = sum(confusion[c].values())
        predicted = sum(confusion[t][c] for t in labels)
        precision = tp / predicted if predicted else None
        recall = tp / actual if actual else None
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None
        per_class[c] = {"images": actual, "precision": precision, "recall": recall, "f1": f1}
    return {
        "evaluated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model_file": os.path.basename(ai_verification.settings.AI_MODEL_PATH),
        "test_dir": os.path.abspath(test_dir),
        "images": total,
        "accuracy": correct / total,
        "min_confidence": min_confidence,
        "true_claims_accepted": (claim_ok / claim_total) if claim_total else None,
        "per_class": per_class,
        "confusion_matrix": confusion,
        "labels": labels,
    }


def to_markdown(r: dict) -> str:
    pct = lambda v: "-" if v is None else f"{v * 100:.1f}%"
    lines = [
        "# AI model evaluation", "",
        f"* Model: `{r['model_file']}`  * Evaluated: {r['evaluated_at']}  * Test images: {r['images']}",
        f"* **Accuracy: {pct(r['accuracy'])}**",
        f"* True claims accepted as a match (confidence >= {r['min_confidence']}): {pct(r['true_claims_accepted'])}",
        "", "| Class | Images | Precision | Recall | F1 |", "|---|---|---|---|---|",
    ]
    for c, m in r["per_class"].items():
        lines.append(f"| {c} | {m['images']} | {pct(m['precision'])} | {pct(m['recall'])} | {pct(m['f1'])} |")
    labels = r["labels"]
    lines += ["", "Confusion matrix (rows = true class, columns = predicted):", "",
              "| true \\ predicted | " + " | ".join(labels) + " |", "|---" * (len(labels) + 1) + "|"]
    for t in labels:
        lines.append(f"| {t} | " + " | ".join(str(r["confusion_matrix"][t][p]) for p in labels) + " |")
    lines += ["", "Small test sets give uncertain numbers. State the test-set size and source with any result."]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--test-dir", required=True)
    p.add_argument("--min-confidence", type=float, default=0.6)
    p.add_argument("--out", default=os.path.dirname(os.path.abspath(__file__)))
    args = p.parse_args()
    result = evaluate(args.test_dir, args.min_confidence)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "results.json"), "w") as f:
        json.dump(result, f, indent=2)
    md = to_markdown(result)
    with open(os.path.join(args.out, "results.md"), "w", encoding="utf-8") as f:
        f.write(md)
    print(md)


if __name__ == "__main__":
    main()
