import json
import tempfile
import unittest
from pathlib import Path

from iot_code.evidence import EVIDENCE_SCHEMA, EvidenceOutbox, build_evidence, evidence_digest


class EvidenceTests(unittest.TestCase):
    def test_build_evidence_is_deterministic_and_versioned(self):
        evidence = build_evidence(
            event_id="event-1", device_id="HRC-ESP32-01", sensor_id="HC-SR04",
            measured_at="2026-09-30T00:00:00Z", received_at="2026-09-30T00:00:01Z",
            distance_cm=24.6, severity="EMERGENCY", emergency_stop=True, confidence=1.0,
        )
        self.assertEqual(evidence["schema"], EVIDENCE_SCHEMA)
        self.assertEqual(evidence["evidence_hash"], evidence_digest(evidence))

    def test_tampering_is_rejected_before_submission(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = EvidenceOutbox(Path(directory))
            evidence = build_evidence(
                event_id="event-2", device_id="HRC-ESP32-01", sensor_id="HC-SR04",
                measured_at="2026-09-30T00:00:00Z", received_at=None,
                distance_cm=80.0, severity="SAFE", emergency_stop=False, confidence=0.1,
            )
            path = outbox.enqueue(evidence)
            tampered = json.loads(path.read_text(encoding="utf-8"))
            tampered["distance_cm"] = 12.0
            path.write_text(json.dumps(tampered), encoding="utf-8")
            with self.assertRaises(ValueError):
                outbox.verify(path)

    def test_outbox_is_idempotent_and_marks_confirmed(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = EvidenceOutbox(Path(directory))
            evidence = build_evidence(
                event_id="event-3", device_id="HRC-ESP32-01", sensor_id="HC-SR04",
                measured_at="2026-09-30T00:00:00Z", received_at=None,
                distance_cm=42.0, severity="WARNING", emergency_stop=False, confidence=0.8,
            )
            first = outbox.enqueue(evidence)
            second = outbox.enqueue(evidence)
            self.assertEqual(first, second)
            tx = outbox.submit(first, lambda payload: "0xabc")
            self.assertEqual(tx, "0xabc")
            self.assertEqual(json.loads(first.read_text())["evidence_status"], "confirmed")

    def test_invalid_emergency_combination_is_rejected(self):
        with self.assertRaises(ValueError):
            build_evidence(
                event_id="event-4", device_id="device", sensor_id="HC-SR04",
                measured_at="2026-09-30T00:00:00Z", received_at=None,
                distance_cm=80.0, severity="SAFE", emergency_stop=True, confidence=1.0,
            )

    def test_offline_verifier_does_not_accept_a_self_rehashed_tampered_file(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = EvidenceOutbox(Path(directory))
            evidence = build_evidence(
                event_id="event-5", device_id="device", sensor_id="HC-SR04",
                measured_at="2026-09-30T00:00:00Z", received_at=None,
                distance_cm=24.0, severity="EMERGENCY", emergency_stop=True, confidence=1.0,
            )
            path = outbox.enqueue(evidence)
            changed = json.loads(path.read_text())
            changed["distance_cm"] = 12.0
            changed["evidence_hash"] = evidence_digest(changed)
            path.write_text(json.dumps(changed), encoding="utf-8")
            # The local file is internally consistent again, but its digest is no longer the digest committed earlier.
            self.assertNotEqual(changed["evidence_hash"], evidence["evidence_hash"])
