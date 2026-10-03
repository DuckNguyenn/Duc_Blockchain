import tempfile
import unittest
from pathlib import Path

from iot_code.evidence import EvidenceOutbox, build_evidence


class ChainPolicyTests(unittest.TestCase):
    def test_non_emergency_is_marked_offchain(self):
        with tempfile.TemporaryDirectory() as directory:
            outbox = EvidenceOutbox(Path(directory))
            evidence = build_evidence(
                event_id="warning-1", device_id="device", sensor_id="HC-SR04",
                measured_at="2026-10-03T00:00:00Z", received_at=None,
                distance_cm=42.0, severity="WARNING", emergency_stop=False, confidence=0.8,
            )
            path = outbox.enqueue(evidence)
            marked = outbox.mark_offchain(path)
            self.assertEqual(marked["evidence_status"], "offchain")
            self.assertEqual(outbox.pending(), [])


if __name__ == "__main__":
    unittest.main()
