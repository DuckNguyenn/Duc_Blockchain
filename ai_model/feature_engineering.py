"""Feature preparation for the single HC-SR04 safety sensor."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

FEATURE_COLUMNS = ["distance_cm", "approach_speed_cm_s"]
LABELS = {"SAFE": 0, "APPROACHING": 1, "EMERGENCY": 2}


def load_recordings(data_dir: str | Path) -> pd.DataFrame:
    files = sorted(Path(data_dir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV recordings found in {data_dir}")
    frames = []
    for path in files:
        frame = pd.read_csv(path)
        if "source_file" not in frame.columns:
            frame["source_file"] = path.name
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    required = {"timestamp", "elapsed_s", "distance_cm", "label"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    return add_features(data)


def add_features(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    for column in ("distance_cm", "elapsed_s"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["distance_cm", "elapsed_s"]).copy()
    frame["approach_speed_cm_s"] = (
        frame.groupby("source_file", sort=False)["distance_cm"].diff()
        / frame.groupby("source_file", sort=False)["elapsed_s"].diff()
    ).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    frame["label_id"] = frame["label"].astype(str).str.upper().map(LABELS).fillna(0).astype(int)
    return frame


def features_from_measurement(distance_cm: float, previous_distance_cm: float | None = None, dt_s: float = 0.1) -> dict[str, float]:
    distance = float(distance_cm)
    previous = distance if previous_distance_cm is None else float(previous_distance_cm)
    return {"distance_cm": distance, "approach_speed_cm_s": (distance - previous) / max(float(dt_s), 1e-6)}
