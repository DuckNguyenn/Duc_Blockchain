"""Causal features matching ESP32 and class-covered recording partitions."""
from __future__ import annotations

import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

LABELS = ["SAFE", "APPROACHING", "EMERGENCY"]
FEATURE_COLUMNS = ["distance_cm", "distance_delta_3", "distance_std_5"]


def load_dataset(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    required = {"source_file", "elapsed_s", "distance_cm", "label"}
    if required - set(frame.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(frame.columns))}")
    frame["label"] = frame["label"].astype(str).str.upper()
    for column in ["elapsed_s", "distance_cm"]:
        frame[column] = pd.to_numeric(frame[column], errors="raise")
    if frame[list(required)].isna().any().any() or not np.isfinite(frame[["elapsed_s", "distance_cm"]]).all().all():
        raise ValueError("Missing or non-finite training measurements")
    if set(frame["label"]) != set(LABELS):
        raise ValueError(f"Expected all labels {LABELS}")
    if not frame["distance_cm"].between(2, 450).all():
        raise ValueError("Sensor faults must be handled separately, not trained as SAFE")
    frame = frame.sort_values(["source_file", "elapsed_s"], kind="stable").reset_index(drop=True)
    if frame.groupby("source_file")["elapsed_s"].diff().dropna().le(0).any():
        raise ValueError("Timestamps must increase strictly within each recording")
    return frame


def make_features(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.sort_values(["source_file", "elapsed_s"], kind="stable").copy()
    grouped = out.groupby("source_file", sort=False)["distance_cm"]
    out["distance_delta_3"] = grouped.diff(3).fillna(0.0)
    out["distance_std_5"] = grouped.transform(lambda s: s.rolling(5, min_periods=1).std(ddof=1).fillna(0.0))
    return out


def recording_splits(frame: pd.DataFrame, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Group whole single-label recordings; enforce all classes in every split."""
    grouped = frame.groupby("source_file")["label"]
    if grouped.nunique().ne(1).any():
        raise ValueError("Mixed-label sessions require a session-stratified split manifest")
    labels = grouped.first()
    rng = np.random.default_rng(seed)
    manifest = {name: [] for name in ["train", "validation", "test"]}
    for label in LABELS:
        sources = np.array(sorted(labels[labels == label].index))
        if len(sources) < 3:
            raise ValueError(f"{label}: need >=3 independent recordings for train/validation/test")
        sources = rng.permutation(sources)
        held = max(1, int(len(sources) * 0.2))
        manifest["test"].extend(sources[:held].tolist())
        manifest["validation"].extend(sources[held:2 * held].tolist())
        manifest["train"].extend(sources[2 * held:].tolist())
    parts = {name: frame[frame["source_file"].isin(sources)].copy() for name, sources in manifest.items()}
    for name, part in parts.items():
        if set(part["label"]) != set(LABELS):
            raise ValueError(f"{name} does not cover all classes")
    return parts


def prepare_data(path: str | Path, seed: int = 42) -> dict:
    raw = load_dataset(path)
    frames = {name: make_features(part) for name, part in recording_splits(raw, seed).items()}
    x = {name: part[FEATURE_COLUMNS].to_numpy(dtype=np.float32) for name, part in frames.items()}
    y = {name: part["label"].map({label: i for i, label in enumerate(LABELS)}).to_numpy(dtype=np.int32) for name, part in frames.items()}
    mean = x["train"].mean(axis=0)
    scale = np.where(x["train"].std(axis=0) < 1e-6, 1.0, x["train"].std(axis=0)).astype(np.float32)
    return {"raw": raw, "frames": frames, "x": x, "y": y, "mean": mean, "scale": scale,
            "normalized": {name: ((values - mean) / scale).astype(np.float32) for name, values in x.items()}}


def split_manifest(data: dict) -> dict:
    return {name: {"recordings": sorted(part["source_file"].unique().tolist()), "rows": len(part),
                   "class_counts": part["label"].value_counts().reindex(LABELS, fill_value=0).to_dict()}
            for name, part in data["frames"].items()}


def metrics(y_true: np.ndarray, predictions: np.ndarray) -> dict:
    report = classification_report(y_true, predictions, labels=[0, 1, 2], target_names=LABELS, output_dict=True, zero_division=0)
    return {"accuracy": float(accuracy_score(y_true, predictions)),
            "macro_f1": float(f1_score(y_true, predictions, labels=[0, 1, 2], average="macro", zero_division=0)),
            "emergency_recall": report["EMERGENCY"]["recall"], "approaching_recall": report["APPROACHING"]["recall"],
            "confusion_matrix": confusion_matrix(y_true, predictions, labels=[0, 1, 2]).tolist(), "per_class": report}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
