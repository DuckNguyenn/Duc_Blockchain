import tempfile
import unittest
from pathlib import Path

from iot_code.evidence import build_evidence
from iot_code.gateway.storage import TelemetryStore


class TelemetryStoreTests(unittest.TestCase):
    def test_saves_telemetry_and_updates_chain_status(self):
        with tempfile.TemporaryDirectory() as directory:
            evidence = build_evidence(
                event_id="event-1",
                device_id="HRC-ESP32-01",
                sensor_id="HC-SR04",
                measured_at="2026-10-03T00:00:00Z",
                received_at="2026-10-03T00:00:01Z",
                distance_cm=24.6,
                severity="EMERGENCY",
                emergency_stop=True,
                confidence=1.0,
            )
            result = {
                "event_id": "event-1",
                "device_id": "HRC-ESP32-01",
                "distance_cm": 24.6,
                "severity": "EMERGENCY",
                "emergency_stop": True,
                "confidence": 1.0,
                "evidence_hash": evidence["evidence_hash"],
                "submission_status": "queued",
            }
            with TelemetryStore(Path(directory) / "telemetry.db") as store:
                store.save(result, evidence, '{"distance_cm":24.6}')
                row = store.connection.execute(
                    "SELECT severity, evidence_status, tx_hash FROM telemetry WHERE event_id = ?",
                    ("event-1",),
                ).fetchone()
                self.assertEqual(row["severity"], "EMERGENCY")
                self.assertEqual(row["evidence_status"], "queued")
                self.assertIsNone(row["tx_hash"])
                store.mark_confirmed("event-1", "0xabc")
                row = store.connection.execute(
                    "SELECT evidence_status, tx_hash FROM telemetry WHERE event_id = ?",
                    ("event-1",),
                ).fetchone()
                self.assertEqual(row["evidence_status"], "confirmed")
                self.assertEqual(row["tx_hash"], "0xabc")


if __name__ == "__main__":
    unittest.main()
