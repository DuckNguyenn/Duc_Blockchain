"""Read the existing ESP32 text protocol and pass measurements to pipeline.py."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone

from iot_code.gateway.pipeline import process_row

MEASUREMENT = re.compile(r"distance_cm,left=([-\d.]+|timeout)cm?,right=([-\d.]+|timeout)cm?")


def parse_line(line: str) -> dict[str, str] | None:
    match = MEASUREMENT.search(line.strip())
    if not match:
        return None
    left, right = match.groups()
    if "timeout" in (left, right):
        return None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "left_cm": left,
        "right_cm": right,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True, help="ESP32 serial port, e.g. COM5")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--device-id", default="HRC-ESP32-01")
    args = parser.parse_args()
    import serial
    with serial.Serial(args.port, args.baud, timeout=2) as port:
        for raw in port:
            row = parse_line(raw.decode(errors="replace"))
            if row:
                print(json.dumps(process_row(row, device_id=args.device_id), ensure_ascii=False))


if __name__ == "__main__":
    main()
