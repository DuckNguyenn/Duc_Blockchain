from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


CONTRACT_ABI = [
    {
        "inputs": [
            {"internalType": "bytes32", "name": "warningId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "logHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "deviceId", "type": "bytes32"},
            {"internalType": "bytes32", "name": "sensorId", "type": "bytes32"},
            {"internalType": "uint8", "name": "severity", "type": "uint8"}
        ],
        "name": "recordWarning",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]


@dataclass
class BlockchainRecorder:
    """Optional audit adapter; never part of local sensor measurement."""

    web3: Any
    account: str
    private_key: str
    contract: Any

    @classmethod
    def from_environment(cls) -> "BlockchainRecorder | None":
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

        rpc_url = os.getenv("HRC_RPC_URL")
        private_key = os.getenv("HRC_GATEWAY_PRIVATE_KEY")
        contract_address = os.getenv("HRC_CONTRACT_ADDRESS")
        if not rpc_url or not private_key or not contract_address:
            return None

        try:
            from web3 import Web3
        except ImportError as exc:
            raise RuntimeError(
                "Blockchain is configured but web3 is not installed. "
                "Run: pip install web3"
            ) from exc

        web3 = Web3(Web3.HTTPProvider(rpc_url))
        if not web3.is_connected():
            raise RuntimeError(f"Cannot connect to blockchain RPC: {rpc_url}")

        account = web3.eth.account.from_key(private_key).address
        contract = web3.eth.contract(
            address=Web3.to_checksum_address(contract_address),
            abi=CONTRACT_ABI,
        )
        return cls(web3, account, private_key, contract)

    def record(self, warning: dict[str, Any]) -> str:
        Web3 = self.web3
        warning_id = Web3.keccak(text=warning["warning_id"])
        log_hash = bytes.fromhex(warning["log_sha256"])
        device_id = Web3.keccak(text=warning["device_id"])
        sensor_id = Web3.keccak(text=warning.get("sensor_id") or "HC-SR04")
        severity = 1 if warning.get("state") == "SENSOR_FAULT" else 0

        transaction = self.contract.functions.recordWarning(
            warning_id,
            log_hash,
            device_id,
            sensor_id,
            severity,
        ).build_transaction(
            {
                "from": self.account,
                "nonce": self.web3.eth.get_transaction_count(self.account),
                "chainId": self.web3.eth.chain_id,
                "gas": 300_000,
                "gasPrice": self.web3.eth.gas_price,
            }
        )
        signed = self.web3.eth.account.sign_transaction(transaction, self.private_key)
        transaction_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction)
        self.web3.eth.wait_for_transaction_receipt(transaction_hash)
        return transaction_hash.hex()