"""Gateway setup errors should be actionable before connecting to hardware/RPC."""
import contextlib
import io
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from iot_code.gateway.blockchain_client import SafetyLogClient
from iot_code.gateway.serial_reader import main


class GatewayCredentialsTests(unittest.TestCase):
    def test_serial_cli_explains_the_pasted_placeholder_key(self):
        settings = {
            "RPC_URL": "http://127.0.0.1:8545",
            "CONTRACT_ADDRESS": "địa chỉ HRCSafetyLog vừa deploy",
            "PRIVATE_KEY": "private key account Hardhat local",
        }
        with patch.dict(os.environ, settings):
            with patch("sys.argv", ["serial_reader", "--port", "COM5", "--write-chain"]):
                with patch("serial.Serial") as port, patch("iot_code.gateway.blockchain_client.Web3.HTTPProvider") as provider:
                    with self.assertRaises(SystemExit) as result:
                        main()
                    self.assertIn("Copy dòng Private Key", str(result.exception))
                    self.assertNotIn(settings["PRIVATE_KEY"], str(result.exception))
                    port.assert_not_called()
                    provider.assert_not_called()

    def test_invalid_contract_address_is_rejected_before_rpc_connection(self):
        for address in ("địa chỉ HRCSafetyLog vừa deploy", "0x" + "0" * 40):
            with self.subTest(address=address), patch(
                "iot_code.gateway.blockchain_client.Web3.HTTPProvider",
                side_effect=AssertionError("Invalid contract address reached RPC setup"),
            ) as provider:
                with self.assertRaisesRegex(ValueError, "CONTRACT_ADDRESS.*contract="):
                    SafetyLogClient("http://127.0.0.1:1", address, "0x" + "1" * 64, "unused.json")
                provider.assert_not_called()

    def test_serial_cli_reports_stopped_rpc_without_opening_port(self):
        settings = {
            "RPC_URL": "http://127.0.0.1:1",
            "CONTRACT_ADDRESS": "0x" + "1" * 40,
            "PRIVATE_KEY": "0x" + "1" * 64,
        }
        with patch.dict(os.environ, settings):
            with patch("sys.argv", ["serial_reader", "--port", "COM5", "--write-chain"]):
                with patch("serial.Serial") as port, patch("iot_code.gateway.blockchain_client.Web3.is_connected", return_value=False):
                    with self.assertRaises(SystemExit) as result:
                        main()
                    self.assertIn("npm.cmd run node", str(result.exception))
                    self.assertNotIn(settings["PRIVATE_KEY"], str(result.exception))
                    port.assert_not_called()

    def test_wallet_address_is_rejected_before_rpc_connection(self):
        address = "0x" + "1" * 40
        with patch("iot_code.gateway.blockchain_client.Web3.HTTPProvider") as provider:
            with self.assertRaisesRegex(ValueError, "địa chỉ ví.*Private Key"):
                SafetyLogClient("http://127.0.0.1:1", address, address, "unused.json")
            provider.assert_not_called()

    def test_serial_cli_reports_invalid_key_without_traceback_or_opening_port(self):
        address = "0x" + "1" * 40
        with patch.dict(os.environ, {"RPC_URL": "http://127.0.0.1:1", "CONTRACT_ADDRESS": address, "PRIVATE_KEY": address}):
            with patch("sys.argv", ["serial_reader", "--port", "COM5", "--write-chain"]), patch("serial.Serial") as port:
                with self.assertRaises(SystemExit) as result:
                    main()
                self.assertIn("Private Key", str(result.exception))
                self.assertNotIn(address, str(result.exception))
                port.assert_not_called()

    def test_offchain_emergency_sets_stop_without_wallet_or_rpc(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = ["serial_reader", "--port", "COM5", "--database", str(root / "telemetry.db"), "--evidence-dir", str(root / "evidence")]
            with patch.dict(os.environ, {"PRIVATE_KEY": "0x" + "1" * 40}), patch("sys.argv", args):
                with patch("serial.Serial") as port, patch("iot_code.gateway.blockchain_client.SafetyLogClient") as client:
                    port.return_value.__enter__.return_value.__iter__.return_value = [b'{"device_id":"esp32","distance_cm":7.2,"state":"EMERGENCY"}\n']
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        main()
                    event = json.loads(output.getvalue())
                    self.assertEqual(event["severity"], "EMERGENCY")
                    self.assertTrue(event["emergency_stop"])
                    self.assertNotIn("tx_hash", event)
                    client.assert_not_called()
