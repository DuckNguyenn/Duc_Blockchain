"""Inspect class coverage of the notebook's 5-fold grouped splitter."""
from pathlib import Path
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from ai_model.tinyml_pipeline import load_dataset, write_json

frame = load_dataset("ai_model/data/single_sensor/processed_3class/dataset_3class.csv")
def folds(data):
    result = []
    for index, (tr, va) in enumerate(StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42).split(
        np.zeros((len(data), 1)), data.label, data.source_file), 1):
        result.append({"fold": index, "train_counts": data.iloc[tr].label.value_counts().to_dict(),
                       "validation_counts": data.iloc[va].label.value_counts().to_dict(),
                       "validation_recordings": sorted(data.iloc[va].source_file.unique().tolist())})
    return result
resampled = frame.copy()
resampled["time_bin"] = np.floor(resampled.elapsed_s).astype(int)
resampled = resampled.groupby(["source_file", "time_bin"], as_index=False).agg(label=("label", "first"))
payload = {"recordings_per_class": frame.groupby("source_file").label.first().value_counts().to_dict(),
           "original_5fold": folds(frame), "one_second_5fold": folds(resampled)}
write_json(Path("docs/notebook_split_audit.json"), payload)
print(payload)
