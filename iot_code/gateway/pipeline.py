"""End-to-end HRC safety pipeline for CSV replay or ESP32 serial input."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from ai_model.feature_engineering import FEATURE_COLUMNS, features_from_measurement

SEVERITY = {"SAFE": 0, "WARNING": 1, "DANGER": 2, "EMERGENCY": 3}


def classify(measurement: dict[str, float], model=None, warning_cm=60.0, danger_cm=30.0) -> tuple[str, bool, float]:
    minimum = measurement["min_distance_cm"]
    if minimum <= danger_cm:
        return "EMERGENCY", True, 1.0
    if minimum <= warning_cm:
        return "WARNING", False, 0.8
    if model is not None:
        anomaly = int(model.predict([[measurement[c] for c in FEATURE_COLUMNS]])[0] == -1)
        if anomaly:
            return "WARNING", False, 0.6
    return "SAFE", False, 0.05


def stable_event_id(device_id: str, timestamp: str, measurement: dict[str, float], severity: str) -> str:
    payload = f"{device_id}|{timestamp}|{measurement['left_cm']:.2f}|{measurement['right_cm']:.2f}|{severity}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def process_row(row: dict[str, str], *, device_id: str, model=None, client=None, warning_cm=60.0, danger_cm=30.0) -> dict:
    timestamp = row.get("timestamp") or datetime.now(timezone.utc).isoformat()
    left = float(row["left_cm"])
    right = float(row["right_cm"])
    measurement = features_from_measurement(left, right)
    severity, emergency_stop, confidence = classify(measurement, model, warning_cm, danger_cm)
    event_id = stable_event_id(device_id, timestamp, measurement, severity)
    result = {
        "event_id": event_id,
        "device_id": device_id,
        "timestamp": timestamp,
        "left_cm": left,
        "right_cm": right,
        "min_distance_cm": measurement["min_distance_cm"],
        "severity": severity,
        "confidence": confidence,
        "emergency_stop": emergency_stop,
        "action": "EMERGENCY_STOP" if emergency_stop else "MONITOR",
    }
    if client is not None:
        result["tx_hash"] = client.record(
            event_id=event_id,
            device_id=device_id,
            timestamp=int(time.time()),
            severity=SEVERITY[severity],
            emergency_stop=emergency_stop,
        )
    return result


def csv_rows(path: str):
    with open(path, newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def main() -> None:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ModuleNotFoundError:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", help="Replay an existing recording")
    parser.add_argument("--model", default=os.getenv("MODEL_PATH", "ai_model/model.joblib"))
    parser.add_argument("--device-id", default=os.getenv("DEVICE_ID", "HRC-ESP32-01"))
    parser.add_argument("--rpc-url", default=os.getenv("RPC_URL"))
    parser.add_argument("--contract-address", default=os.getenv("CONTRACT_ADDRESS"))
    parser.add_argument("--private-key", default=os.getenv("PRIVATE_KEY"))
    parser.add_argument("--abi", default="contracts/abi/HRCSafetyLog.json")
    parser.add_argument("--write-chain", action="store_true", help="Submit records to the deployed contract")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    if not args.csv:
        parser.error("--csv is required for the replay demo; serial mode can be added after wiring validation")

    model = None
    if Path(args.model).exists():
        import joblib
        artifact = joblib.load(args.model)
        model = artifact["model"] if isinstance(artifact, dict) else artifact

    client = None
    if args.write_chain:
        required = [args.rpc_url, args.contract_address, args.private_key]
        if not all(required):
            parser.error("--write-chain requires RPC_URL, CONTRACT_ADDRESS, and PRIVATE_KEY")
        from iot_code.gateway.blockchain_client import SafetyLogClient
        client = SafetyLogClient(args.rpc_url, args.contract_address, args.private_key, args.abi)

    for index, row in enumerate(csv_rows(args.csv)):
        if index >= args.limit:
            break
        print(json.dumps(process_row(row, device_id=args.device_id, model=model, client=client), ensure_ascii=False))


if __name__ == "__main__":
    main()
