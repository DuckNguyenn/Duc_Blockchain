"""Small Web3 adapter; keeps blockchain I/O out of safety classification logic."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from eth_utils import keccak
from web3 import Web3


class SafetyLogClient:
    def __init__(self, rpc_url: str, contract_address: str, private_key: str, abi_path: str):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError(f"Cannot connect to RPC endpoint {rpc_url}")
        self.account = self.web3.eth.account.from_key(private_key)
        abi = json.loads(Path(abi_path).read_text(encoding="utf-8"))
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )

    @staticmethod
    def hash_text(value: str) -> bytes:
        return keccak(text=value)

    def record(self, *, event_id: str, device_id: str, timestamp: int, severity: int, emergency_stop: bool) -> str:
        event_hash = self.hash_text(event_id)
        device_hash = self.hash_text(device_id)
        nonce = self.web3.eth.get_transaction_count(self.account.address)
        tx = self.contract.functions.recordEvent(
            event_hash, device_hash, timestamp, severity, emergency_stop
        ).build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "chainId": self.web3.eth.chain_id,
            "gas": 500_000,
            "gasPrice": self.web3.eth.gas_price,
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError(f"Blockchain transaction failed: {tx_hash.hex()}")
        return tx_hash.hex()

    def record_evidence(self, evidence: dict[str, Any]) -> str:
        """Submit a v1 evidence digest while keeping the envelope off-chain."""
        severity = {"SAFE": 0, "WARNING": 1, "DANGER": 2, "EMERGENCY": 3}[evidence["severity"]]
        from datetime import datetime
        measured_at = int(datetime.fromisoformat(evidence["measured_at"].replace("Z", "+00:00")).timestamp())
        evidence_hash = bytes.fromhex(evidence["evidence_hash"])
        device_hash = self.hash_text(evidence["device_id"])
        schema_hash = self.hash_text(evidence["schema"])
        nonce = self.web3.eth.get_transaction_count(self.account.address)
        tx = self.contract.functions.recordEvidence(
            evidence_hash,
            device_hash,
            measured_at,
            severity,
            bool(evidence["emergency_stop"]),
            schema_hash,
        ).build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "chainId": self.web3.eth.chain_id,
            "gas": 500_000,
            "gasPrice": self.web3.eth.gas_price,
        })
        signed = self.account.sign_transaction(tx)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt.status != 1:
            raise RuntimeError(f"Blockchain transaction failed: {tx_hash.hex()}")
        return tx_hash.hex()
