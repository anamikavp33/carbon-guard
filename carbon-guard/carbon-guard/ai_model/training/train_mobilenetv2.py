"""Fine-tune MobileNetV2 for Carbon Guard and export it to ONNX for the backend.

Run in Google Colab (free GPU) or any machine with TensorFlow:

    !pip install "tensorflow==2.17.*" "tf2onnx==1.16.*" "onnx==1.17.*"
    !python train_mobilenetv2.py --data /content/dataset --out /content/weights

Dataset layout (see ../README.md for how to collect it and the licence rules):

    dataset/
      train/  other/  solar_panel/  tree_plantation/  water_harvesting/
      val/    other/  solar_panel/  tree_plantation/  water_harvesting/

Output (copy both files to carbon-guard/ai_model/weights/):

    carbon_guard_mobilenetv2.onnx
    carbon_guard_mobilenetv2.onnx.labels.json

The class order is alphabetical (Keras' default) and is written to the labels file, which the backend
reads, so the two can never get out of step. Preprocessing in the backend (resize to 224x224, scale
pixels to [-1, 1]) matches the `preprocess_input` used here.

Status: written for the project, NOT yet run (needs the dataset). Report the real numbers from
../evaluation/evaluate.py, never the training accuracy printed here.
"""
import argparse
import json
import os

IMG_SIZE = 224
EXPECTED = ["other", "solar_panel", "tree_plantation", "water_harvesting"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True, help="folder containing train/ and val/")
    p.add_argument("--out", default="weights")
    p.add_argument("--epochs", type=int, default=10, help="epochs with the base model frozen")
    p.add_argument("--fine-tune-epochs", type=int, default=5, help="extra epochs with the top layers unfrozen")
    p.add_argument("--batch", type=int, default=32)
    args = p.parse_args()

    import tensorflow as tf
    from tensorflow import keras

    def load(split, shuffle):
        return keras.utils.image_dataset_from_directory(
            os.path.join(args.data, split), image_size=(IMG_SIZE, IMG_SIZE), batch_size=args.batch,
            label_mode="int", shuffle=shuffle, seed=42)

    train, val = load("train", True), load("val", False)
    labels = train.class_names
    if labels != EXPECTED:
        raise SystemExit(f"Expected class folders {EXPECTED}, found {labels}")

    augment = keras.Sequential([
        keras.layers.RandomFlip("horizontal"),
        keras.layers.RandomRotation(0.05),
        keras.layers.RandomZoom(0.1),
        keras.layers.RandomContrast(0.1),
    ], name="augment")

    base = keras.applications.MobileNetV2(input_shape=(IMG_SIZE, IMG_SIZE, 3), include_top=False, weights="imagenet")
    base.trainable = False

    # The exported model takes images ALREADY scaled to [-1, 1] (the backend does that), so
    # preprocessing is applied to the datasets here, not inside the model.
    prep = keras.applications.mobilenet_v2.preprocess_input
    train = train.map(lambda x, y: (prep(augment(x, training=True)), y)).prefetch(tf.data.AUTOTUNE)
    val = val.map(lambda x, y: (prep(x), y)).prefetch(tf.data.AUTOTUNE)

    inputs = keras.Input(shape=(IMG_SIZE, IMG_SIZE, 3), name="input")
    x = base(inputs, training=False)
    x = keras.layers.GlobalAveragePooling2D()(x)
    x = keras.layers.Dropout(0.3)(x)
    outputs = keras.layers.Dense(len(labels), activation="softmax", name="probs")(x)
    model = keras.Model(inputs, outputs)

    model.compile(optimizer=keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    stop = keras.callbacks.EarlyStopping(patience=3, restore_best_weights=True)
    model.fit(train, validation_data=val, epochs=args.epochs, callbacks=[stop])

    # Fine-tune the top of the base model with a small learning rate.
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    model.compile(optimizer=keras.optimizers.Adam(1e-5), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train, validation_data=val, epochs=args.fine_tune_epochs, callbacks=[stop])

    os.makedirs(args.out, exist_ok=True)
    import tf2onnx
    spec = (tf.TensorSpec((None, IMG_SIZE, IMG_SIZE, 3), tf.float32, name="input"),)
    onnx_path = os.path.join(args.out, "carbon_guard_mobilenetv2.onnx")
    tf2onnx.convert.from_keras(model, input_signature=spec, opset=13, output_path=onnx_path)
    with open(onnx_path + ".labels.json", "w") as f:
        json.dump(labels, f)
    print("Saved", onnx_path, "and its labels file. Now run ../evaluation/evaluate.py on the TEST set.")


if __name__ == "__main__":
    main()
