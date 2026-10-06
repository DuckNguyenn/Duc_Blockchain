"""The gateway must include pending transactions when choosing a nonce."""
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from iot_code.gateway.blockchain_client import SafetyLogClient


class GatewayNonceTests(unittest.TestCase):
    def test_pending_nonce_is_used_for_events_and_evidence(self):
        for kind in ("event", "evidence"):
            with self.subTest(kind=kind):
                client = SafetyLogClient.__new__(SafetyLogClient)
                eth = Mock()
                eth.chain_id = 31337
                eth.gas_price = 1
                eth.get_transaction_count.side_effect = lambda _address, block_identifier="latest": 2587 if block_identifier == "pending" else 2586
                eth.wait_for_transaction_receipt.return_value = SimpleNamespace(status=1)
                client.web3 = SimpleNamespace(eth=eth)
                client.account = SimpleNamespace(address="0x" + "1" * 40, sign_transaction=lambda tx: SimpleNamespace(raw_transaction=tx))
                builder = Mock()
                builder.build_transaction.side_effect = lambda tx: tx
                client.contract = SimpleNamespace(functions=SimpleNamespace(recordEvent=lambda *_: builder, recordEvidence=lambda *_: builder))

                def send(tx):
                    if tx["nonce"] < 2587:
                        raise ValueError("Nonce too low. Expected nonce to be 2587 but got 2586")
                    return bytes.fromhex("a" * 64)
                eth.send_raw_transaction.side_effect = send
                if kind == "event":
                    tx = client.record(event_id="event", device_id="esp32", timestamp=1, severity=3, emergency_stop=True)
                else:
                    tx = client.record_evidence({"evidence_hash": "a" * 64, "device_id": "esp32", "measured_at": "2026-10-05T00:00:00Z",
                                                 "schema": "sonarchain.evidence.v1", "severity": "EMERGENCY", "emergency_stop": True})
                self.assertEqual(tx, "0x" + "a" * 64)
                eth.get_transaction_count.assert_called_once_with(client.account.address, "pending")
