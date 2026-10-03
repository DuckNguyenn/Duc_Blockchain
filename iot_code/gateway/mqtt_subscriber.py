"""Subscribe to ESP32 telemetry over MQTT and feed the safety evidence pipeline."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from iot_code.evidence import EvidenceOutbox
from iot_code.gateway.pipeline import process_row


def parse_payload(payload: bytes | str) -> dict[str, str] | None:
    """Normalize an MQTT JSON message into the pipeline's row shape."""
    if isinstance(payload, bytes):
        payload = payload.decode("utf-8", errors="replace")
    try:
        value: Any = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(value, dict) or value.get("distance_cm") is None:
        return None
    try:
        distance = float(value["distance_cm"])
    except (TypeError, ValueError):
        return None
    if distance < 0:
        return None
    timestamp = value.get("timestamp") or value.get("measured_at")
    if not timestamp and value.get("timestamp_ms") is not None:
        timestamp = datetime.fromtimestamp(
            float(value["timestamp_ms"]) / 1000, tz=timezone.utc
        ).isoformat()
    return {
        "timestamp": str(timestamp or datetime.now(timezone.utc).isoformat()),
        "distance_cm": str(distance),
        "dt_s": str(value.get("dt_s", 0.1)),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="HRC MQTT telemetry gateway")
    parser.add_argument("--host", default=os.getenv("MQTT_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MQTT_PORT", "1883")))
    parser.add_argument("--topic", default=os.getenv("MQTT_TOPIC", "hrc/telemetry/#"))
    parser.add_argument("--device-id", default=os.getenv("DEVICE_ID", "HRC-ESP32-01"))
    parser.add_argument("--evidence-dir", default="data/evidence_outbox")
    parser.add_argument("--write-chain", action="store_true")
    parser.add_argument("--rpc-url", default=os.getenv("RPC_URL"))
    parser.add_argument("--contract-address", default=os.getenv("CONTRACT_ADDRESS"))
    parser.add_argument("--private-key", default=os.getenv("PRIVATE_KEY"))
    parser.add_argument("--abi", default="contracts/abi/HRCSafetyLog.json")
    return parser


def main() -> None:
    try:
        import paho.mqtt.client as mqtt
    except ModuleNotFoundError as error:
        raise SystemExit("MQTT gateway requires paho-mqtt; run: pip install -r requirements.txt") from error

    args = build_parser().parse_args()
    client = None
    if args.write_chain:
        required = [args.rpc_url, args.contract_address, args.private_key]
        if not all(required):
            raise SystemExit("--write-chain requires RPC_URL, CONTRACT_ADDRESS, and PRIVATE_KEY")
        from iot_code.gateway.blockchain_client import SafetyLogClient
        client = SafetyLogClient(args.rpc_url, args.contract_address, args.private_key, args.abi)

    outbox = EvidenceOutbox(Path(args.evidence_dir))
    previous_distance: float | None = None

    def on_connect(mqtt_client, _userdata, _flags, reason_code, _properties=None):
        if int(reason_code) == 0:
            mqtt_client.subscribe(args.topic, qos=1)
            print(json.dumps({"mqtt": "connected", "host": args.host, "port": args.port, "topic": args.topic}))
        else:
            print(json.dumps({"mqtt": "connect_failed", "reason": str(reason_code)}))

    def on_message(_mqtt_client, _userdata, message):
        nonlocal previous_distance
        row = parse_payload(message.payload)
        if row is None:
            print(json.dumps({"mqtt": "ignored", "topic": message.topic, "reason": "invalid telemetry"}))
            return
        device_id = args.device_id
        try:
            payload = json.loads(message.payload.decode("utf-8"))
            device_id = str(payload.get("device_id") or device_id)
        except (UnicodeDecodeError, json.JSONDecodeError):
            pass
        result = process_row(
            row,
            device_id=device_id,
            client=None,
            previous_min_cm=previous_distance,
            evidence_outbox=outbox,
        )
        previous_distance = result["distance_cm"]
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
        print(json.dumps({"topic": message.topic, **result}, ensure_ascii=False))

    try:
        mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="hrc-safety-gateway")
    except AttributeError:  # paho-mqtt 1.x compatibility
        mqtt_client = mqtt.Client(client_id="hrc-safety-gateway")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_message = on_message
    mqtt_client.connect(args.host, args.port, keepalive=60)
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()
