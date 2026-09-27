"""Train the unsupervised anomaly detector used by the live gateway."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import joblib
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from feature_engineering import FEATURE_COLUMNS, load_recordings


def train(data_dir: str, model_path: str, metrics_path: str) -> None:
    data = load_recordings(data_dir)
    x = data[FEATURE_COLUMNS]
    y = data["label_id"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.25, random_state=42, stratify=y
    )
    # The model learns the normal operating envelope from SAFE samples only.
    normal_train = x_train[y_train == 0]
    if len(normal_train) < 10:
        raise ValueError("Need at least 10 SAFE samples for training")
    model = Pipeline([
        ("scale", StandardScaler()),
        ("detector", IsolationForest(n_estimators=150, contamination=0.08, random_state=42)),
    ])
    model.fit(normal_train)
    predictions = model.predict(x_test)
    predicted_anomaly = (predictions == -1).astype(int)
    actual_anomaly = (y_test > 0).astype(int)
    report = classification_report(actual_anomaly, predicted_anomaly, output_dict=True, zero_division=0)
    artifact = {
        "model": model,
        "feature_columns": FEATURE_COLUMNS,
        "thresholds_cm": {"warning": 60.0, "danger": 30.0},
        "training_rows": int(len(normal_train)),
    }
    Path(model_path).parent.mkdir(parents=True, exist_ok=True)
    Path(metrics_path).parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, model_path)
    Path(metrics_path).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"model": model_path, "metrics": metrics_path, "rows": len(data)}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data/raw")
    parser.add_argument("--model-path", default="ai/model.joblib")
    parser.add_argument("--metrics-path", default="data/processed/metrics.json")
    args = parser.parse_args()
    train(args.data_dir, args.model_path, args.metrics_path)
