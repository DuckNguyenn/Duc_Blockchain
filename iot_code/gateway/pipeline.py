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
import numpy as np

from ai_model.feature_engineering import FEATURE_COLUMNS, features_from_measurement
from iot_code.evidence import EvidenceOutbox, build_evidence

SEVERITY = {"SAFE": 0, "WARNING": 1, "DANGER": 2, "EMERGENCY": 3}


def classify(
    measurement: dict[str, float],
    model=None,
    warning_cm=60.0,
    danger_cm=30.0,
    confidence_threshold=0.85,
) -> tuple[str, bool, float]:
    """Classify one measurement with hard safety rules before AI.

    A hybrid artifact must satisfy both supervised-classifier confidence and
    IsolationForest agreement before it can add a WARNING outside the hard
    distance zones. Legacy IsolationForest-only artifacts remain supported.
    """
    minimum = measurement["distance_cm"]
    if minimum <= danger_cm:
        return "EMERGENCY", True, 1.0
    if minimum <= warning_cm:
        return "WARNING", False, 0.8
    if model is None:
        return "SAFE", False, 0.05

    row = [[measurement[c] for c in FEATURE_COLUMNS]]
    if isinstance(model, dict) and "classifier" in model and "isolation_forest" in model and "autoencoder" in model:
        classifier = model["classifier"]
        isolation_forest = model["isolation_forest"]
        autoencoder = model["autoencoder"]
        autoencoder_scaler = model["autoencoder_scaler"]
        classifier_state = int(classifier.predict(row)[0])
        classifier_confidence = float(classifier.predict_proba(row).max())
        if_flag = bool(isolation_forest.predict(row)[0] == -1)
        scaled = autoencoder_scaler.transform(row)
        reconstruction_error = float(np.mean((scaled - autoencoder.predict(scaled)) ** 2, axis=1)[0])
        if_threshold = float(model.get("if_anomaly_threshold", 0.0))
        ae_threshold = float(model.get("ae_reconstruction_threshold", 0.0))
        fusion = str(model.get("anomaly_fusion", "and"))
        ae_flag = reconstruction_error >= ae_threshold
        anomaly_flag = if_flag and ae_flag if fusion == "and" else if_flag or ae_flag
        threshold = float(model.get("ai_confidence_threshold", confidence_threshold))
        if classifier_state > 0 and classifier_confidence >= threshold and anomaly_flag:
            return "WARNING", False, classifier_confidence
        return "SAFE", False, max(0.05, classifier_confidence if classifier_state == 0 else 0.0)

    if isinstance(model, dict) and "classifier" in model and "anomaly_model" in model:
        classifier = model["classifier"]
        anomaly_model = model["anomaly_model"]
        classifier_state = int(classifier.predict(row)[0])
        classifier_confidence = float(classifier.predict_proba(row).max())
        anomaly_flag = int(anomaly_model.predict(row)[0] == -1)
        threshold = float(model.get("ai_confidence_threshold", confidence_threshold))
        if classifier_state > 0 and classifier_confidence >= threshold and anomaly_flag:
            return "WARNING", False, classifier_confidence
        return "SAFE", False, max(0.05, classifier_confidence if classifier_state == 0 else 0.0)

    if isinstance(model, dict) and "model" in model:
        model = model["model"]
    anomaly = int(model.predict(row)[0] == -1)
    if anomaly:
        return "WARNING", False, 0.6
    return "SAFE", False, 0.05


def stable_event_id(device_id: str, timestamp: str, measurement: dict[str, float], severity: str) -> str:
    payload = f"{device_id}|{timestamp}|{measurement['distance_cm']:.2f}|{severity}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def process_row(
    row: dict[str, str],
    *,
    device_id: str,
    model=None,
    client=None,
    warning_cm=60.0,
    danger_cm=30.0,
    confidence_threshold=0.85,
    previous_min_cm: float | None = None,
    evidence_outbox: EvidenceOutbox | None = None,
) -> dict:
    timestamp = row.get("timestamp") or datetime.now(timezone.utc).isoformat()
    distance = float(row["distance_cm"])
    dt_s = float(row.get("dt_s", 0.1) or 0.1)
    measurement = features_from_measurement(distance, previous_min_cm, dt_s)
    severity, emergency_stop, confidence = classify(
        measurement, model, warning_cm, danger_cm, confidence_threshold
    )
    event_id = stable_event_id(device_id, timestamp, measurement, severity)
    result = {
        "event_id": event_id,
        "device_id": device_id,
        "timestamp": timestamp,
        "distance_cm": distance,
        "min_distance_cm": distance,
        "severity": severity,
        "confidence": confidence,
        "emergency_stop": emergency_stop,
        "action": "EMERGENCY_STOP" if emergency_stop else "MONITOR",
    }
    evidence = build_evidence(
        event_id=event_id,
        device_id=device_id,
        sensor_id="HC-SR04",
        measured_at=timestamp,
        received_at=datetime.now(timezone.utc).isoformat(),
        distance_cm=distance,
        severity=severity,
        emergency_stop=emergency_stop,
        confidence=confidence,
        policy_version=f"thresholds.v{warning_cm:g}-{danger_cm:g}",
        model_version="provided" if model is not None else "none",
    )
    result["evidence_hash"] = evidence["evidence_hash"]
    if evidence_outbox is not None:
        evidence_outbox.enqueue(evidence)
    if client is not None and evidence_outbox is None:
        if hasattr(client, "record_evidence"):
            result["tx_hash"] = client.record_evidence(evidence)
        else:
            result["tx_hash"] = client.record(event_id=event_id, device_id=device_id, timestamp=int(time.time()), severity=SEVERITY[severity], emergency_stop=emergency_stop)
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
    parser.add_argument("--evidence-dir", default="data/evidence_outbox", help="Durable off-chain evidence outbox")
    parser.add_argument("--retry-outbox", action="store_true", help="Retry all queued evidence submissions")
    args = parser.parse_args()
    if not args.csv and not args.retry_outbox:
        parser.error("--csv is required unless --retry-outbox is used")

    model = None
    warning_cm = 60.0
    danger_cm = 30.0
    confidence_threshold = 0.85
    if Path(args.model).exists():
        import joblib
        artifact = joblib.load(args.model)
        model = artifact
        if isinstance(artifact, dict):
            thresholds = artifact.get("thresholds_cm", {})
            warning_cm = float(thresholds.get("warning", warning_cm))
            danger_cm = float(thresholds.get("danger", danger_cm))
            confidence_threshold = float(
                artifact.get("ai_confidence_threshold", confidence_threshold)
            )

    client = None
    if args.write_chain:
        required = [args.rpc_url, args.contract_address, args.private_key]
        if not all(required):
            parser.error("--write-chain requires RPC_URL, CONTRACT_ADDRESS, and PRIVATE_KEY")
        from iot_code.gateway.blockchain_client import SafetyLogClient
        client = SafetyLogClient(args.rpc_url, args.contract_address, args.private_key, args.abi)

    outbox = EvidenceOutbox(Path(args.evidence_dir))
    if args.retry_outbox:
        if client is None:
            parser.error("--retry-outbox requires --write-chain")
        for pending_path in outbox.pending():
            try:
                print(json.dumps({"evidence_hash": outbox.verify(pending_path)["evidence_hash"], "tx_hash": outbox.submit(pending_path, client.record_evidence), "status": "confirmed"}))
            except Exception as error:
                print(json.dumps({"path": str(pending_path), "status": "pending", "error": str(error)}))
        return

    previous_min_cm = None
    for index, row in enumerate(csv_rows(args.csv)):
        if index >= args.limit:
            break
        result = process_row(
            row,
            device_id=args.device_id,
            model=model,
            client=client,
            warning_cm=warning_cm,
            danger_cm=danger_cm,
            confidence_threshold=confidence_threshold,
            previous_min_cm=previous_min_cm,
            evidence_outbox=outbox,
        )
        evidence_path = outbox.path_for(result["evidence_hash"])
        if result["severity"] != "EMERGENCY":
            outbox.mark_offchain(evidence_path)
            result["submission_status"] = "offchain"
        elif client is not None:
            try:
                result["tx_hash"] = outbox.submit(evidence_path, client.record_evidence)
                result["submission_status"] = "confirmed"
            except Exception as error:
                result["submission_status"] = "pending"
                result["submission_error"] = str(error)
        else:
            result["submission_status"] = "queued"
        previous_min_cm = result["distance_cm"]
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
