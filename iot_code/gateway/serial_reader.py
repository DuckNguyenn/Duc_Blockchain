"""Read ESP32 telemetry over Serial and persist it through the gateway."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from iot_code.evidence import EvidenceOutbox
from iot_code.gateway.pipeline import process_row
from iot_code.gateway.storage import TelemetryStore

MEASUREMENT = re.compile(r"distance_cm,(?:distance|left)=([-\d.]+|timeout)(?:cm)?$")


def parse_line(line: str) -> dict[str, str] | None:
    text = line.strip()
    try:
        payload = json.loads(text)
        distance = payload.get("distance_cm") if isinstance(payload, dict) else None
        if distance is not None:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "distance_cm": str(distance),
                "dt_s": "0.1",
            }
        return None
    except json.JSONDecodeError:
        pass
    match = MEASUREMENT.search(text)
    if not match or match.group(1) == "timeout":
        return None
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "distance_cm": match.group(1), "dt_s": "0.1"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ESP32 Serial safety gateway")
    parser.add_argument("--port", required=True, help="ESP32 serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--device-id", default="HRC-ESP32-01")
    parser.add_argument("--database", default="data/telemetry.db", help="SQLite database path")
    parser.add_argument("--evidence-dir", default="data/evidence_outbox")
    parser.add_argument("--write-chain", action="store_true")
    parser.add_argument("--rpc-url")
    parser.add_argument("--contract-address")
    parser.add_argument("--private-key")
    parser.add_argument("--abi", default="contracts/abi/HRCSafetyLog.json")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.write_chain and not all((args.rpc_url, args.contract_address, args.private_key)):
        raise SystemExit("--write-chain requires --rpc-url, --contract-address, and --private-key")

    import serial

    client = None
    if args.write_chain:
        from iot_code.gateway.blockchain_client import SafetyLogClient
        client = SafetyLogClient(args.rpc_url, args.contract_address, args.private_key, args.abi)

    outbox = EvidenceOutbox(Path(args.evidence_dir))
    previous_distance: float | None = None
    with TelemetryStore(args.database) as store, serial.Serial(args.port, args.baud, timeout=2) as port:
        for raw in port:
            raw_text = raw.decode(errors="replace").strip()
            row = parse_line(raw_text)
            if row is None:
                continue
            result = process_row(
                row,
                device_id=args.device_id,
                previous_min_cm=previous_distance,
                evidence_outbox=outbox,
            )
            previous_distance = result["distance_cm"]
            result["submission_status"] = "queued"
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
            evidence = outbox.verify(evidence_path)
            store.save(result, evidence, raw_payload=raw_text)
            print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
