import json
import tempfile
import unittest
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient
from iot_code.evidence import EvidenceOutbox
from iot_code.gateway.api import app, configure_database
from iot_code.gateway.pipeline import process_row
from iot_code.gateway.serial_reader import parse_line
from iot_code.gateway.storage import TelemetryStore
from iot_code.gateway.api import telemetry_socket
from fastapi import WebSocketDisconnect


class LivePipelineTests(unittest.TestCase):
    def test_serial_fault_survives_to_api_and_websocket(self):
        row = parse_line('{"device_id":"ESP32-HRC-01","state":"SENSOR_FAULT","distance_cm":null}')
        self.assertIsNotNone(row)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outbox = EvidenceOutbox(root / "evidence")
            result = process_row(row, device_id=row["device_id"], evidence_outbox=outbox)
            self.assertEqual(result["severity"], "SENSOR_FAULT")
            self.assertIsNone(result["distance_cm"])
            db = root / "telemetry.db"
            with TelemetryStore(db) as store:
                store.save(result, outbox.verify(outbox.path_for(result["evidence_hash"])))
            configure_database(db)
            try:
                with TestClient(app) as client:
                    self.assertEqual(client.get("/api/telemetry/latest").json()["telemetry"]["severity"], "SENSOR_FAULT")
                    with client.websocket_connect("/ws/telemetry") as socket:
                        self.assertEqual(socket.receive_json()["severity"], "SENSOR_FAULT")
            finally:
                configure_database("data/telemetry.db")

    def test_edge_approaching_remains_warning_outside_distance_threshold(self):
        row = parse_line('{"state":"APPROACHING","distance_cm":120}')
        self.assertEqual(process_row(row, device_id="esp32")["severity"], "WARNING")

    def test_edge_safe_cannot_override_hard_emergency(self):
        row = parse_line('{"state":"SAFE","distance_cm":24}')
        self.assertTrue(process_row(row, device_id="esp32")["emergency_stop"])

    def test_nonfinite_distance_becomes_sensor_fault(self):
        row = parse_line('{"state":"SAFE","distance_cm":"nan"}')
        self.assertEqual(process_row(row, device_id="esp32")["severity"], "SENSOR_FAULT")

    def test_direct_client_submits_only_emergency(self):
        from unittest.mock import Mock
        client = Mock()
        for distance in (100, 45, None):
            result = process_row({"distance_cm": distance}, device_id="esp32", client=client)
            self.assertNotIn("tx_hash", result)
        client.record_evidence.assert_not_called()
        result = process_row({"distance_cm": 24}, device_id="esp32", client=client)
        client.record_evidence.assert_called_once()
        self.assertTrue(result["emergency_stop"])

    def test_websocket_publishes_confirmation_when_latest_row_id_does_not_change(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            outbox = EvidenceOutbox(root / "evidence")
            result = process_row({"distance_cm": 20}, device_id="esp32", evidence_outbox=outbox)
            result["submission_status"] = "queued"
            with TelemetryStore(root / "telemetry.db") as store:
                store.save(result, outbox.verify(outbox.path_for(result["evidence_hash"])))
                configure_database(root / "telemetry.db")
                updates = []
                class Socket:
                    async def accept(self): pass
                    async def send_json(self, row): updates.append(row)
                ticks = 0
                async def advance(_delay):
                    nonlocal ticks
                    ticks += 1
                    if ticks == 1:
                        store.mark_confirmed(result["event_id"], "0x" + "a" * 64)
                    if ticks >= 3:
                        raise WebSocketDisconnect()
                try:
                    with patch("iot_code.gateway.api.asyncio.sleep", advance):
                        asyncio.run(telemetry_socket(Socket()))
                    self.assertEqual([row["evidence_status"] for row in updates], ["queued", "confirmed"])
                finally:
                    configure_database("data/telemetry.db")
