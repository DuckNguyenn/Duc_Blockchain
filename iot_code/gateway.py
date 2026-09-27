from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .blockchain import BlockchainRecorder
from .logging_service import sha256_hex, write_warning


ALERT_STATES = frozenset({"WARNING", "SENSOR_FAULT"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_telemetry(line: str) -> dict[str, Any] | None:
    """Parse one JSON line emitted by the ESP32; ignore boot/status text."""
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) and "state" in payload else None


def build_warning(payload: dict[str, Any], sequence: int) -> dict[str, Any]:
    """Create a tamper-evident warning record from one sensor sample."""
    state = str(payload.get("state", "SENSOR_FAULT"))
    warning = {
        "warning_id": f"WARN-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{sequence:06d}",
        "event_type": (
            "DISTANCE_BELOW_THRESHOLD" if state == "WARNING" else "SENSOR_TIMEOUT"
        ),
        "device_id": payload.get("device_id", "ESP32-HRC-01"),
        "sensor_id": payload.get("sensor_id", "HC-SR04"),
        "timestamp_utc": utc_now(),
        "timestamp_ms": payload.get("timestamp_ms"),
        "distance_cm": payload.get("distance_cm"),
        "state": state,
        "sequence": payload.get("seq"),
    }
    warning["log_sha256"] = sha256_hex(warning)
    return warning


def process_lines(
    lines: Iterable[str],
    warning_dir: Path,
    blockchain: BlockchainRecorder | None = None,
    cooldown_seconds: float = 5.0,
) -> list[Path]:
    """Persist rate-limited warnings read from ESP32 Serial JSON telemetry."""
    written: list[Path] = []
    sequence = 0
    last_alert_at: dict[tuple[str, str], float] = {}

    for line in lines:
        payload = parse_telemetry(line)
        if payload is None:
            continue

        device_id = str(payload.get("device_id", "ESP32-HRC-01"))
        state = str(payload.get("state"))
        if state == "SAFE":
            last_alert_at.pop((device_id, "WARNING"), None)
            last_alert_at.pop((device_id, "SENSOR_FAULT"), None)
            continue
        if state not in ALERT_STATES:
            continue

        key = (device_id, state)
        now = time.monotonic()
        if now - last_alert_at.get(key, float("-inf")) < cooldown_seconds:
            continue
        last_alert_at[key] = now

        sequence += 1
        warning = build_warning(payload, sequence)
        path = write_warning(warning, warning_dir)
        written.append(path)
        print(f"[WARNING] {path.name} state={warning['state']} hash={warning['log_sha256']}")

        if blockchain is not None:
            try:
                transaction_hash = blockchain.record(warning)
                print(f"[BLOCKCHAIN] warning_tx={transaction_hash}")
            except Exception as error:
                print(f"[BLOCKCHAIN_ERROR] {error}", file=sys.stderr)

    return written


def _serial_lines(port: str, baud: int) -> Iterable[str]:
    try:
        import serial
    except ImportError as exc:
        raise RuntimeError(
            "Serial input requires pyserial; run pip install -r requirements.txt"
        ) from exc

    with serial.Serial(port, baudrate=baud, timeout=1) as connection:
        while True:
            raw = connection.readline()
            if raw:
                yield raw.decode("utf-8", errors="replace")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ESP32 HC-SR04 warning log gateway")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--port", help="ESP32 serial port, for example COM3")
    source.add_argument("--stdin", action="store_true", help="Read JSON telemetry from stdin")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--warning-dir", type=Path, default=Path("data/incidents"))
    parser.add_argument("--cooldown-seconds", type=float, default=5.0)
    parser.add_argument("--blockchain", action="store_true", help="Record warning hash on-chain")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    lines: Iterable[str] = sys.stdin if args.stdin else _serial_lines(args.port, args.baud)
    recorder = BlockchainRecorder.from_environment() if args.blockchain else None
    process_lines(lines, args.warning_dir, recorder, args.cooldown_seconds)


if __name__ == "__main__":
    main()