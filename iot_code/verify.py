from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import evidence_digest


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify an HC-SR04 warning log hash")
    parser.add_argument("log", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.log.read_text(encoding="utf-8"))
    valid = payload.get("evidence_hash") == evidence_digest(payload)
    print(
        "VALID: warning matches its stored SHA-256 hash"
        if valid
        else "INVALID: warning was changed"
    )
    raise SystemExit(0 if valid else 1)


if __name__ == "__main__":
    main()
