"""Small Web3 adapter; keeps blockchain I/O out of safety classification logic."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from eth_utils import keccak
from eth_account import Account
from web3 import Web3


class SafetyLogClient:
    def __init__(self, rpc_url: str, contract_address: str, private_key: str, abi_path: str):
        key = private_key.strip() if isinstance(private_key, str) else ""
        if re.fullmatch(r"(?:0[xX])?[0-9a-fA-F]{40}", key):
            raise ValueError(
                "PRIVATE_KEY đang là địa chỉ ví (20 byte). Copy dòng Private Key "
                "của tài khoản Reporter/Owner trong terminal Hardhat: 0x + 64 ký tự hex."
            )
        if not re.fullmatch(r"(?:0[xX])?[0-9a-fA-F]{64}", key):
            raise ValueError(
                "PRIVATE_KEY phải là khóa 32 byte: 0x + 64 ký tự hex. "
                "Copy dòng Private Key của tài khoản Owner/Reporter trong terminal Hardhat; "
                "không dùng nội dung mô tả trong hướng dẫn."
            )
        try:
            self.account = Account.from_key(key)
        except (ValueError, TypeError):
            raise ValueError("PRIVATE_KEY không hợp lệ. Dùng khóa của tài khoản Reporter/Owner.") from None
        address = contract_address.strip() if isinstance(contract_address, str) else ""
        if not re.fullmatch(r"0[xX][0-9a-fA-F]{40}", address) or int(address, 16) == 0:
            raise ValueError(
                "CONTRACT_ADDRESS phải là địa chỉ HRCSafetyLog khác 0: 0x + 40 ký tự hex. "
                "Copy giá trị contract= từ npm.cmd run deploy."
            )
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not self.web3.is_connected():
            raise ConnectionError(
                "Không kết nối được RPC_URL. Chạy npm.cmd run node trong thư mục contracts "
                "và giữ terminal đó mở; kiểm tra RPC_URL trỏ đúng node."
            )
        abi = json.loads(Path(abi_path).read_text(encoding="utf-8"))
        self.contract = self.web3.eth.contract(
            address=Web3.to_checksum_address(address), abi=abi
        )

    @staticmethod
    def hash_text(value: str) -> bytes:
        return keccak(text=value)

    def record(self, *, event_id: str, device_id: str, timestamp: int, severity: int, emergency_stop: bool) -> str:
        event_hash = self.hash_text(event_id)
        device_hash = self.hash_text(device_id)
        nonce = self.web3.eth.get_transaction_count(self.account.address, "pending")
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
        return Web3.to_hex(tx_hash)

    def record_evidence(self, evidence: dict[str, Any]) -> str:
        """Submit a v1 evidence digest while keeping the envelope off-chain."""
        severity = {"SAFE": 0, "WARNING": 1, "DANGER": 2, "EMERGENCY": 3}[evidence["severity"]]
        from datetime import datetime
        measured_at = int(datetime.fromisoformat(evidence["measured_at"].replace("Z", "+00:00")).timestamp())
        evidence_hash = bytes.fromhex(evidence["evidence_hash"])
        device_hash = self.hash_text(evidence["device_id"])
        schema_hash = self.hash_text(evidence["schema"])
        nonce = self.web3.eth.get_transaction_count(self.account.address, "pending")
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
        return Web3.to_hex(tx_hash)
