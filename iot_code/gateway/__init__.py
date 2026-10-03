"""Compatibility API for the original JSON telemetry gateway.

The package also contains the newer CSV pipeline modules. Keeping these small
helpers here preserves the public import used by existing callers and tests:
``from iot_code.gateway import parse_telemetry``.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from iot_code.logging_service import sha256_hex, write_warning

ALERT_STATES = frozenset({"WARNING", "EMERGENCY", "SENSOR_FAULT"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_telemetry(line: str) -> dict[str, Any] | None:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) and "state" in payload else None


def build_warning(payload: dict[str, Any], sequence: int) -> dict[str, Any]:
    state = str(payload.get("state", "SENSOR_FAULT"))
    warning = {
        "warning_id": f"WARN-{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{sequence:06d}",
        "event_type": "EMERGENCY_STOP" if state == "EMERGENCY" else "DISTANCE_BELOW_THRESHOLD" if state == "WARNING" else "SENSOR_TIMEOUT",
        "device_id": payload.get("device_id", "ESP32-HRC-01"),
        "sensor_id": payload.get("sensor_id", "HC-SR04"),
        "timestamp_utc": utc_now(),
        "timestamp_ms": payload.get("timestamp_ms"),
        "distance_cm": payload.get("distance_cm"),
        "state": state,
        "emergency_stop": state == "EMERGENCY",
        "sequence": payload.get("seq"),
    }
    warning["log_sha256"] = sha256_hex(warning)
    return warning


def process_lines(
    lines: Iterable[str],
    warning_dir: Path,
    blockchain=None,
    cooldown_seconds: float = 5.0,
) -> list[Path]:
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
        if blockchain is not None:
            blockchain.record(warning)
    return written


__all__ = ["build_warning", "parse_telemetry", "process_lines"]
