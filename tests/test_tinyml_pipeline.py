import tempfile
import unittest
from pathlib import Path
import numpy as np
import pandas as pd
from ai_model.tinyml_pipeline import FEATURE_COLUMNS, LABELS, make_features, recording_splits
from ai_model.train_keras_tflite import write_c_array


class TinyMlPipelineTests(unittest.TestCase):
    def test_partition_keeps_recordings_whole_and_covers_all_classes(self):
        frame = pd.DataFrame([{"source_file": f"{label}-{group}", "elapsed_s": i * 0.18,
                               "distance_cm": 100 + i, "label": label}
                              for label in LABELS for group in range(3) for i in range(8)])
        parts = recording_splits(frame)
        sets = [set(part.source_file) for part in parts.values()]
        for part in parts.values():
            self.assertEqual(set(part.label), set(LABELS))
        self.assertFalse(sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2])
        self.assertEqual(sum(map(len, parts.values())), len(frame))

    def test_refuses_insufficient_independent_recordings(self):
        frame = pd.DataFrame([{"source_file": label, "label": label} for label in LABELS])
        with self.assertRaisesRegex(ValueError, ">=3"):
            recording_splits(frame)

    def test_features_match_firmware_warmup_and_sample_std(self):
        distances = [100, 99, 96, 90, 88, 80]
        rows = pd.DataFrame({"source_file": ["a"] * 6 + ["b"], "elapsed_s": list(range(6)) + [0], "distance_cm": distances + [40]})
        actual = make_features(rows)[FEATURE_COLUMNS].to_numpy()
        for i, distance in enumerate(distances):
            window = distances[max(0, i - 4):i + 1]
            expected = [distance, distance - distances[i - 3] if i >= 3 else 0,
                        np.std(window, ddof=1) if i else 0]
            np.testing.assert_allclose(actual[i], expected)
        np.testing.assert_allclose(actual[-1], [40, 0, 0])

    def test_exported_cpp_has_valid_integer_float_literals(self):
        with tempfile.TemporaryDirectory() as directory:
            write_c_array(b"\x01\x02", Path(directory), np.array([0., 2., 0.3]), np.ones(3))
            text = (Path(directory) / "model_data.cc").read_text()
            self.assertIn("0.0f, 2.0f, 0.3f", text)
            self.assertNotIn("{1f", text)
