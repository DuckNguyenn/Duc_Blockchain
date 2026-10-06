"""Chain receipt waits must not block live serial telemetry."""
import contextlib
import io
import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from iot_code.evidence import EvidenceOutbox
from iot_code.gateway.serial_reader import main


class SerialSubmissionTests(unittest.TestCase):
    def test_serial_samples_are_persisted_while_receipt_is_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "telemetry.db"
            entered, release, completed = threading.Event(), threading.Event(), threading.Event()
            observed = []
            class Client:
                def record_evidence(self, _evidence):
                    with contextlib.closing(sqlite3.connect(db)) as connection:
                        observed.append(connection.execute("SELECT count(*) FROM telemetry").fetchone()[0])
                    entered.set()
                    release.wait(3)
                    completed.set()
                    return "0x" + "a" * 64
            def samples():
                yield b'{"distance_cm":20,"state":"EMERGENCY","device_id":"esp32"}\n'
                if not entered.wait(2):
                    raise AssertionError("Submission worker did not start")
                yield b'{"distance_cm":90,"state":"SAFE","device_id":"esp32"}\n'
                with contextlib.closing(sqlite3.connect(db)) as connection:
                    rows = connection.execute("SELECT severity FROM telemetry ORDER BY id").fetchall()
                observed.append(rows)
                release.set()
                completed.wait(2)
            args = ["serial_reader", "--port", "COM5", "--write-chain", "--database", str(db), "--evidence-dir", str(root / "evidence")]
            settings = {"RPC_URL": "http://127.0.0.1:1", "CONTRACT_ADDRESS": "0x" + "1" * 40, "PRIVATE_KEY": "test-fixture"}
            try:
                with patch.dict(os.environ, settings), patch("sys.argv", args):
                    with patch("serial.Serial") as port, patch("iot_code.gateway.blockchain_client.SafetyLogClient", return_value=Client()):
                        port.return_value.__enter__.return_value.__iter__.return_value = samples()
                        with contextlib.redirect_stdout(io.StringIO()):
                            main()
                self.assertEqual(observed[0], 1, "EMERGENCY must be in SQLite before sending the transaction")
                self.assertEqual(observed[1], [("EMERGENCY",), ("SAFE",)], "SAFE must arrive while the first receipt is pending")
                with contextlib.closing(sqlite3.connect(db)) as connection:
                    status, tx_hash = connection.execute("SELECT evidence_status, tx_hash FROM telemetry ORDER BY id LIMIT 1").fetchone()
                self.assertEqual(status, "confirmed")
                self.assertEqual(tx_hash, "0x" + "a" * 64)
            finally:
                release.set()

    def test_submission_failure_retains_retryable_evidence_and_live_safe_sample(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            db = root / "telemetry.db"
            pending = threading.Event()
            updates = []

            class Client:
                def record_evidence(self, _evidence):
                    raise ConnectionError("RPC disconnected during submission")

            def on_update(result):
                updates.append(result)
                pending.set()

            def samples():
                yield b'{"distance_cm":20,"state":"EMERGENCY","device_id":"esp32"}\n'
                if not pending.wait(2):
                    raise AssertionError("Chain failure was not reported")
                yield b'{"distance_cm":90,"state":"SAFE","device_id":"esp32"}\n'

            args = ["serial_reader", "--port", "COM5", "--write-chain", "--database", str(db), "--evidence-dir", str(root / "evidence")]
            settings = {"RPC_URL": "http://127.0.0.1:1", "CONTRACT_ADDRESS": "0x" + "1" * 40, "PRIVATE_KEY": "test-fixture"}
            with patch.dict(os.environ, settings), patch("sys.argv", args):
                with patch("serial.Serial") as port, patch("iot_code.gateway.blockchain_client.SafetyLogClient", return_value=Client()):
                    port.return_value.__enter__.return_value.__iter__.return_value = samples()
                    with patch("iot_code.gateway.submission_worker.emit_result", on_update), contextlib.redirect_stdout(io.StringIO()):
                        main()
            with contextlib.closing(sqlite3.connect(db)) as connection:
                rows = connection.execute("SELECT severity, evidence_status FROM telemetry ORDER BY id").fetchall()
            self.assertEqual(rows, [("EMERGENCY", "pending"), ("SAFE", "offchain")])
            self.assertEqual(updates[0]["submission_status"], "pending")
            self.assertIn("RPC disconnected", updates[0]["submission_error"])
            outbox = EvidenceOutbox(root / "evidence")
            retryable = outbox.pending()
            self.assertEqual(len(retryable), 1)
            self.assertEqual(outbox.verify(retryable[0])["severity"], "EMERGENCY")
