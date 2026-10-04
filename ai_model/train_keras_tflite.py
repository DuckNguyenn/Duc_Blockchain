"""Train the 6-feature ultrasonic classifier and export an int8 TFLite Micro model.

Run from the repository root:
    python ai_model/train_keras_tflite.py

The exported model consumes the six raw features used by the notebook. Feature
normalization is embedded in the Keras model, so the ESP32 only needs to build
those six features and apply the TFLite input quantization parameters.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import tensorflow as tf

LABELS = ["SAFE", "APPROACHING", "EMERGENCY"]
FEATURE_COLUMNS = [
    "distance_cm",
    "approach_speed_cm_s",
    "distance_delta_3",
    "distance_std_5",
    "distance_mean_5",
    "speed_mean_5",
]


def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(["source_file", "elapsed_s"]).copy()
    grouped = out.groupby("source_file", sort=False)
    dt = grouped["elapsed_s"].diff()
    dd = grouped["distance_cm"].diff()
    out["approach_speed_cm_s"] = (
        dd / dt.replace(0, np.nan)
    ).replace([np.inf, -np.inf], np.nan)
    out["approach_speed_cm_s"] = (
        out["approach_speed_cm_s"].clip(-500, 500).fillna(0.0)
    )
    out["distance_delta_3"] = grouped["distance_cm"].diff(3).fillna(0.0)
    out["distance_std_5"] = grouped["distance_cm"].transform(
        lambda s: s.rolling(5, min_periods=1).std().fillna(0.0)
    )
    out["distance_mean_5"] = grouped["distance_cm"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    out["speed_mean_5"] = grouped["approach_speed_cm_s"].transform(
        lambda s: s.rolling(5, min_periods=1).mean()
    )
    return out


def load_dataset(path: Path) -> tuple[np.ndarray, np.ndarray]:
    frame = pd.read_csv(path)
    required = {"source_file", "elapsed_s", "distance_cm", "label"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Dataset thiếu cột: {sorted(missing)}")

    frame["elapsed_s"] = pd.to_numeric(frame["elapsed_s"], errors="coerce")
    frame["distance_cm"] = pd.to_numeric(frame["distance_cm"], errors="coerce")
    frame = frame.dropna(
        subset=["source_file", "elapsed_s", "distance_cm", "label"]
    ).copy()
    frame["label"] = frame["label"].astype(str).str.upper()
    if set(frame["label"].unique()) != set(LABELS):
        raise ValueError(f"Nhãn không đúng: {sorted(frame['label'].unique())}")

    features = make_features(frame)[FEATURE_COLUMNS].astype("float32").to_numpy()
    labels = frame["label"].map({name: i for i, name in enumerate(LABELS)}).to_numpy(
        dtype="int32"
    )
    return features, labels


def build_model(x_normalized: np.ndarray) -> tf.keras.Model:
    # Normalization is performed before the model so the exported graph stays
    # small and fully int8-compatible. The same mean/scale are exported for C++.
    model = tf.keras.Sequential(
        [
            tf.keras.Input(shape=(len(FEATURE_COLUMNS),), dtype=tf.float32),
            tf.keras.layers.Dense(16, activation="relu"),
            tf.keras.layers.Dense(8, activation="relu"),
            tf.keras.layers.Dense(len(LABELS), activation="softmax"),
        ],
        name="ultrasonic_safety_classifier",
    )


    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=1e-3),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def write_c_array(
    model_bytes: bytes,
    output_dir: Path,
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    header = output_dir / "model_data.h"
    source = output_dir / "model_data.cc"
    values = ", ".join(f"0x{byte:02x}" for byte in model_bytes)
    mean_values = ", ".join(f"{value:.9g}f" for value in feature_mean)
    scale_values = ", ".join(f"{value:.9g}f" for value in feature_scale)
    source.write_text(
        "#include \"model_data.h\"\n\n"
        "alignas(16) const unsigned char g_model_data[] = {\n"
        f"  {values}\n"
        "};\n"
        "const unsigned int g_model_data_len = sizeof(g_model_data);\n"
        f"const float g_feature_mean[6] = {{{mean_values}}};\n"
        f"const float g_feature_scale[6] = {{{scale_values}}};\n",
        encoding="utf-8",
    )
    header.write_text(
        "#pragma once\n\n"
        "extern const unsigned char g_model_data[];\n"
        "extern const unsigned int g_model_data_len;\n"
        "extern const float g_feature_mean[6];\n"
        "extern const float g_feature_scale[6];\n",
        encoding="utf-8",
    )


def export_int8(
    model: tf.keras.Model,
    x_normalized: np.ndarray,
    output_dir: Path,
    feature_mean: np.ndarray,
    feature_scale: np.ndarray,
) -> None:
    def representative_data():
        for row in x_normalized[:: max(1, len(x_normalized) // 500)][:500]:
            yield [row.reshape(1, -1).astype(np.float32)]

    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_data
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    model_bytes = converter.convert()

    output_dir.mkdir(parents=True, exist_ok=True)
    tflite_path = output_dir / "ultrasonic_safety_int8.tflite"
    tflite_path.write_bytes(model_bytes)
    write_c_array(model_bytes, output_dir, feature_mean, feature_scale)

    interpreter = tf.lite.Interpreter(model_content=model_bytes)
    interpreter.allocate_tensors()
    input_info = interpreter.get_input_details()[0]
    output_info = interpreter.get_output_details()[0]
    metadata = {
        "labels": LABELS,
        "features": FEATURE_COLUMNS,
        "normalization": {
            "mean": feature_mean.tolist(),
            "scale": feature_scale.tolist(),
        },
        "input": {
            "shape": input_info["shape"].tolist(),
            "dtype": str(input_info["dtype"]),
            "scale": float(input_info["quantization"][0]),
            "zero_point": int(input_info["quantization"][1]),
        },
        "output": {
            "shape": output_info["shape"].tolist(),
            "dtype": str(output_info["dtype"]),
            "scale": float(output_info["quantization"][0]),
            "zero_point": int(output_info["quantization"][1]),
        },
        "model_bytes": len(model_bytes),
        "tensor_arena_start_bytes": 16 * 1024,
    }
    (output_dir / "model_metadata.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    print(json.dumps(metadata, indent=2))
    print(f"Exported: {tflite_path}")
    print(f"Exported: {output_dir / 'model_data.cc'}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("ai_model/data/single_sensor/processed_3class/dataset_3class.csv"),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("esp32_safety_idf/main/model"),
    )
    parser.add_argument("--epochs", type=int, default=80)
    args = parser.parse_args()

    tf.keras.utils.set_random_seed(42)
    x, y = load_dataset(args.dataset)
    feature_mean = x.mean(axis=0)
    feature_scale = x.std(axis=0)
    feature_scale = np.where(feature_scale < 1e-6, 1.0, feature_scale)
    x_normalized = ((x - feature_mean) / feature_scale).astype("float32")
    model = build_model(x_normalized)
    model.fit(
        x_normalized,
        y,
        epochs=args.epochs,
        batch_size=32,
        validation_split=0.2,
        shuffle=False,
        verbose=2,
    )
    export_int8(
        model,
        x_normalized,
        args.output_dir,
        feature_mean,
        feature_scale,
    )


if __name__ == "__main__":
    main()
