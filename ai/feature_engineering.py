"""Feature preparation shared by the training notebook and the live gateway."""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

FEATURE_COLUMNS = [
    "left_cm",
    "right_cm",
    "min_distance_cm",
    "distance_delta_cm",
    "approach_speed_cm_s",
]
LABELS = {"SAFE": 0, "APPROACHING": 1, "DANGER": 2, "RETREATING": 0}


def load_recordings(data_dir: str | Path) -> pd.DataFrame:
    files = sorted(Path(data_dir).glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV recordings found in {data_dir}")
    frames = []
    for path in files:
        frame = pd.read_csv(path)
        frame["source_file"] = path.name
        frames.append(frame)
    data = pd.concat(frames, ignore_index=True)
    required = {"timestamp", "elapsed_s", "left_cm", "right_cm", "label"}
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    return add_features(data)


def add_features(data: pd.DataFrame) -> pd.DataFrame:
    frame = data.copy()
    for column in ("left_cm", "right_cm", "elapsed_s"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna(subset=["left_cm", "right_cm", "elapsed_s"]).copy()
    frame["min_distance_cm"] = frame[["left_cm", "right_cm"]].min(axis=1)
    frame["distance_delta_cm"] = frame["left_cm"] - frame["right_cm"]
    frame["approach_speed_cm_s"] = (
        frame.groupby("source_file", sort=False)["min_distance_cm"].diff()
        / frame.groupby("source_file", sort=False)["elapsed_s"].diff()
    )
    frame["approach_speed_cm_s"] = (
        frame["approach_speed_cm_s"].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    )
    frame["label_id"] = frame["label"].astype(str).str.upper().map(LABELS).fillna(0).astype(int)
    return frame


def features_from_measurement(left_cm: float, right_cm: float, previous_min_cm: float | None = None, dt_s: float = 0.1) -> dict[str, float]:
    minimum = min(float(left_cm), float(right_cm))
    previous = minimum if previous_min_cm is None else float(previous_min_cm)
    return {
        "left_cm": float(left_cm),
        "right_cm": float(right_cm),
        "min_distance_cm": minimum,
        "distance_delta_cm": float(left_cm) - float(right_cm),
        "approach_speed_cm_s": (minimum - previous) / max(float(dt_s), 1e-6),
    }
