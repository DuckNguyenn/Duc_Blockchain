"""Select on grouped validation, test once, export ESP32-compatible INT8.

Run: python -m ai_model.train_keras_tflite
Candidates are saved separately from the currently flashed firmware model.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
from ai_model.tinyml_pipeline import FEATURE_COLUMNS, LABELS, metrics, prepare_data, split_manifest, write_json


def float_literal(value: float) -> str:
    text = format(float(value), ".9g")
    if "." not in text and "e" not in text.lower():
        text += ".0"
    return text + "f"


def write_c_array(blob: bytes, output: Path, mean: np.ndarray, scale: np.ndarray) -> None:
    output.mkdir(parents=True, exist_ok=True)
    count = len(FEATURE_COLUMNS)
    rows = [", ".join(f"0x{value:02x}" for value in blob[i:i + 16]) for i in range(0, len(blob), 16)]
    (output / "model_data.h").write_text(
        "#pragma once\nextern const unsigned char g_model_data[];\nextern const unsigned int g_model_data_len;\n"
        f"extern const float g_feature_mean[{count}];\nextern const float g_feature_scale[{count}];\n", encoding="utf-8")
    (output / "model_data.cc").write_text(
        '#include "model_data.h"\nalignas(16) const unsigned char g_model_data[] = {\n  '
        + ",\n  ".join(rows) + "\n};\nconst unsigned int g_model_data_len = sizeof(g_model_data);\n"
        + f"const float g_feature_mean[{count}] = {{{', '.join(map(float_literal, mean))}}};\n"
        + f"const float g_feature_scale[{count}] = {{{', '.join(map(float_literal, scale))}}};\n", encoding="utf-8")


def train_and_export(data: dict, output: Path, epochs: int = 150, seed: int = 42) -> dict:
    import tensorflow as tf
    from sklearn.utils.class_weight import compute_class_weight
    weights = compute_class_weight("balanced", classes=np.arange(3), y=data["y"]["train"])
    candidates, trained, histories = [], {}, {}
    for hidden in [(), (4,), (8,), (16, 8)]:
        tf.keras.utils.set_random_seed(seed)
        name = "linear" if not hidden else "mlp_" + "_".join(map(str, hidden))
        layers = [tf.keras.Input(shape=(len(FEATURE_COLUMNS),))]
        layers += [tf.keras.layers.Dense(size, activation="relu", kernel_regularizer=tf.keras.regularizers.l2(1e-3)) for size in hidden]
        layers.append(tf.keras.layers.Dense(3, activation="softmax"))
        model = tf.keras.Sequential(layers, name=name)
        model.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="sparse_categorical_crossentropy", metrics=["accuracy"])
        history = model.fit(data["normalized"]["train"], data["y"]["train"],
                            validation_data=(data["normalized"]["validation"], data["y"]["validation"]),
                            epochs=epochs, batch_size=32, class_weight=dict(enumerate(map(float, weights))),
                            callbacks=[tf.keras.callbacks.EarlyStopping(monitor="val_loss", patience=20, min_delta=1e-4, restore_best_weights=True),
                                       tf.keras.callbacks.ReduceLROnPlateau(monitor="val_loss", patience=7, factor=0.5, min_lr=1e-5)], verbose=2)
        pred = model.predict(data["normalized"]["validation"], verbose=0).argmax(axis=1)
        candidates.append({"name": name, "parameters": model.count_params(), "validation": metrics(data["y"]["validation"], pred)})
        trained[name] = model
        histories[name] = {key: [float(value) for value in values] for key, values in history.history.items()}
    selected = max(candidates, key=lambda row: (row["validation"]["macro_f1"], row["validation"]["emergency_recall"], -row["parameters"]))
    model = trained[selected["name"]]
    train_pred = model.predict(data["normalized"]["train"], verbose=0).argmax(axis=1)
    float_pred = model.predict(data["normalized"]["test"], verbose=0).argmax(axis=1)
    rng = np.random.default_rng(seed)
    calibration = data["normalized"]["train"][rng.permutation(len(data["y"]["train"]))[:500]]
    def representative_data():
        for row in calibration:
            yield [row.reshape(1, -1).astype(np.float32)]
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.representative_dataset = representative_data
    converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
    converter.inference_input_type = tf.int8
    converter.inference_output_type = tf.int8
    blob = converter.convert()
    interpreter = tf.lite.Interpreter(model_content=blob)
    interpreter.allocate_tensors()
    inp, out = interpreter.get_input_details()[0], interpreter.get_output_details()[0]
    assert inp["dtype"] == np.int8 and out["dtype"] == np.int8
    assert inp["shape"].tolist() == [1, len(FEATURE_COLUMNS)] and out["shape"].tolist() == [1, 3]
    input_scale, input_zero = inp["quantization"]
    scaled = data["normalized"]["test"] / input_scale
    rounded = np.sign(scaled) * np.floor(np.abs(scaled) + 0.5)  # C++ lround parity
    quantized = np.clip(rounded + input_zero, -128, 127).astype(np.int8)
    outputs = []
    for row in quantized:
        interpreter.set_tensor(inp["index"], row.reshape(1, -1))
        interpreter.invoke()
        outputs.append(interpreter.get_tensor(out["index"])[0].tolist())
    int8_pred = np.asarray(outputs).argmax(axis=1)
    report = {"selected": selected["name"], "candidates": candidates, "train": metrics(data["y"]["train"], train_pred),
              "test_float": metrics(data["y"]["test"], float_pred), "test_int8": metrics(data["y"]["test"], int8_pred),
              "float_int8_agreement": float(np.mean(float_pred == int8_pred)),
              "input_saturation_fraction": float(np.mean((rounded + input_zero < -128) | (rounded + input_zero > 127))),
              "split": split_manifest(data), "seed": seed}
    # Report the currently implemented firmware policy separately from raw AI.
    firmware_pred = np.where(data["x"]["test"][:, 0] <= 30, 2, int8_pred)
    report["test_firmware_policy"] = metrics(data["y"]["test"], firmware_pred)
    output.mkdir(parents=True, exist_ok=True)
    (output / "ultrasonic_safety_int8.tflite").write_bytes(blob)
    model.save(output / "selected_model.keras")
    write_c_array(blob, output, data["mean"], data["scale"])
    metadata = {"labels": LABELS, "features": FEATURE_COLUMNS, "window_size": 5, "std_ddof": 1,
                "normalization": {"mean": data["mean"].tolist(), "scale": data["scale"].tolist()},
                "input": {"shape": inp["shape"].tolist(), "scale": float(input_scale), "zero_point": int(input_zero), "dtype": "int8"},
                "output": {"shape": out["shape"].tolist(), "scale": float(out["quantization"][0]), "zero_point": int(out["quantization"][1]), "dtype": "int8"},
                "model_bytes": len(blob), "hard_distance_rule_cm": 30.0,
                "training_median_dt_s": float(data["raw"].groupby("source_file")["elapsed_s"].diff().median()),
                "operators": sorted({op["op_name"] for op in interpreter._get_ops_details() if op["op_name"] != "DELEGATE"})}
    write_json(output / "model_metadata.json", metadata)
    write_json(output / "metrics.json", report)
    write_json(output / "history.json", histories)
    write_json(output / "parity_vectors.json", {"raw_features": data["x"]["test"][:20].tolist(),
               "int8_input": quantized[:20].tolist(), "int8_output": outputs[:20], "expected_label_id": int8_pred[:20].tolist()})
    print(f"Selected on validation: {selected['name']}; test INT8 accuracy={report['test_int8']['accuracy']:.4f}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("ai_model/data/single_sensor/processed_3class/dataset_3class.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("ai_model/artifacts/esp32_candidate"))
    parser.add_argument("--epochs", type=int, default=150)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--check-data", action="store_true", help="Validate grouped partitions without TensorFlow")
    args = parser.parse_args()
    data = prepare_data(args.dataset, args.seed)
    write_json(args.output_dir / "split_manifest.json", split_manifest(data))
    if args.check_data:
        print(split_manifest(data))
    else:
        train_and_export(data, args.output_dir, args.epochs, args.seed)


if __name__ == "__main__":
    main()
