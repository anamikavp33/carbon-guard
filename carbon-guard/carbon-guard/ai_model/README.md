# AI image verification module

**Current state (honest):** the backend's inference code is finished and tested (with a tiny hand-made
test model), and the training and evaluation scripts are written. **No trained model exists yet**,
because there is no labelled dataset. Until a model file is installed, every submission's AI check
reports `status: "unavailable"`, earns 0 points, and the submission goes to manual review. Nothing is
simulated or guessed.

```
ai_model/
├── README.md                     this file
├── training/train_mobilenetv2.py fine-tune MobileNetV2 (run in Google Colab), export to ONNX
├── evaluation/evaluate.py        measure accuracy on a test set with the backend's own code
└── weights/                      put the .onnx model + .labels.json here (not committed to Git)
```

## Why MobileNetV2 + ONNX

* **MobileNetV2** is small (about 14 MB), fast on a laptop CPU, and pretrained on ImageNet, so
  fine-tuning needs only a few hundred photos per class. It was suggested in the project brief.
* Plain ImageNet classes do **not** include "tree plantation" or "solar installation", so the model must be
  fine-tuned on our 4 classes: `tree_plantation`, `solar_panel`, `water_harvesting`, and `other`
  (anything else; essential so the model can say "this is not any activity").
* Training uses TensorFlow in Colab, but the backend only needs **onnxruntime** (a small package that works
  on Python 3.12/Windows). Nobody has to install TensorFlow locally.

## How the backend uses it (`backend/services/ai_verification.py`)

1. Loads `ai_model/weights/carbon_guard_mobilenetv2.onnx` and `...onnx.labels.json` once
   (another path can be set with `AI_MODEL_PATH` in `backend/.env`).
2. Resizes the photo to 224x224 RGB, scales pixels to [-1, 1], runs the model.
3. `predicted_class` = the most likely class; `matched` = it equals the claimed activity **and** the confidence is
   at least `ai_min_confidence` (0.6, adjustable by admins).
4. Score: `confidence x 60` points if matched, else 0. If the model confidently sees a *different* activity, the
   submission gets the `activity_mismatch` review flag.

**Limitation:** recognising a tree, panel or tank in a photo does **not** prove that the user did the activity,
that it is new, where it is, or that it deserves credits. It is one signal among several, and an admin decides.

## Step 1: build the dataset

Target: at least **150 images per class** for training, 40 for validation, and 40 for testing.

```
dataset/
  train/ other/ solar_panel/ tree_plantation/ water_harvesting/
  val/   (same four folders)
  test/  (same four folders)  <- never used for training
```

Sources, in order of preference. Record every source in `dataset/SOURCES.md` (URL, licence, count).

1. **Photos taken by the team** (planted saplings, rooftop panels, tanks/recharge pits in your area). Best for
   the test set because they look like real submissions.
2. **Wikimedia Commons** images under CC BY / CC BY-SA / public domain (keep the attribution).
3. **Open Images Dataset** (Google): images are listed as CC BY 2.0. Check each image's licence field.
4. Kaggle datasets **only** if their licence allows academic use and redistribution of derived models.

Do not scrape search engines or social media, do not use photos of identifiable people without consent,
and do not commit the dataset to Git (it is large and may have licence conditions).

For `other`, include things that could be confused with the activities: lawns, houses, roofs without
panels, glass buildings, buckets, swimming pools, random street photos.

## Step 2: train (Google Colab, about 20-40 minutes)

1. Zip the `dataset/` folder, upload it to Google Drive.
2. New Colab notebook → *Runtime → Change runtime type → T4 GPU*.
3. Cells:
   ```python
   from google.colab import drive; drive.mount('/content/drive')
   !unzip -q /content/drive/MyDrive/dataset.zip -d /content/
   !pip install -q "tensorflow==2.17.*" "tf2onnx==1.16.*" "onnx==1.17.*"
   # upload ai_model/training/train_mobilenetv2.py to the Colab file panel, then:
   !python train_mobilenetv2.py --data /content/dataset --out /content/weights
   ```
4. Download `weights/carbon_guard_mobilenetv2.onnx` and `weights/carbon_guard_mobilenetv2.onnx.labels.json`
   into `carbon-guard/ai_model/weights/`.
5. Restart the backend. `GET /health` now shows `"ai_model": "available"`.

## Step 3: evaluate honestly

```bat
cd carbon-guard\backend
venv\Scripts\activate
python ..\ai_model\evaluation\evaluate.py --test-dir D:\path\to\dataset\test
```

It runs **the backend's own inference code** on every test image and writes `evaluation/results.md` and
`results.json` (accuracy, per-class precision/recall/F1, confusion matrix, and how many true claims are
accepted at the current confidence threshold). Report only these measured numbers, with the test-set size
and sources. Training accuracy is not a valid result. If the test set is small (under 40 per class), say
the numbers are uncertain.

The script was checked on 2026-10-25 with a tiny fake colour-based model and synthetic images, which only
proves that the script runs. It says nothing about real accuracy.

## Fallback

No model file, unreadable model, missing onnxruntime, or an error during inference: the AI result is
`unavailable` or `error`, it earns 0 points, the submission goes to manual review, and nobody's
Trust Score changes. The rest of the system keeps working.
