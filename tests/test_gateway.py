import json
import tempfile
import unittest
from pathlib import Path

from iot_code.gateway import build_warning, parse_telemetry, process_lines
from iot_code.logging_service import verify_sha256


class GatewayTests(unittest.TestCase):
    def test_parse_telemetry_ignores_boot_text(self):
        self.assertIsNone(parse_telemetry("HRC Safety Log ultrasonic distance logger ready"))
        payload = parse_telemetry('{"state":"WARNING","distance_cm":42.7}')
        self.assertEqual(payload["state"], "WARNING")

    def test_build_warning_is_sensor_specific_and_hash_verifiable(self):
        warning = build_warning(
            {"state": "WARNING", "distance_cm": 42.7, "sensor_id": "HC-SR04"},
            1,
        )
        self.assertEqual(warning["event_type"], "DISTANCE_BELOW_THRESHOLD")
        self.assertEqual(warning["sensor_id"], "HC-SR04")
        self.assertNotIn("camera_id", warning)
        self.assertNotIn("relay", warning)
        self.assertTrue(verify_sha256(warning))

    def test_process_lines_writes_warning_but_not_safe_sample(self):
        lines = [
            json.dumps({"state": "SAFE", "distance_cm": 120}),
            json.dumps({"state": "WARNING", "distance_cm": 42.7}),
        ]
        with tempfile.TemporaryDirectory() as directory:
            paths = process_lines(lines, Path(directory), cooldown_seconds=0)
            self.assertEqual(len(paths), 1)
            payload = json.loads(paths[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["state"], "WARNING")
            self.assertTrue(verify_sha256(payload))

    def test_sensor_fault_is_logged(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = process_lines(
                [json.dumps({"state": "SENSOR_FAULT", "distance_cm": None})],
                Path(directory),
                cooldown_seconds=0,
            )
            payload = json.loads(paths[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["event_type"], "SENSOR_TIMEOUT")
            self.assertTrue(verify_sha256(payload))


if __name__ == "__main__":
    unittest.main()