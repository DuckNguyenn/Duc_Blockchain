from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_hex(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload)).hexdigest()


def verify_sha256(payload: dict[str, Any]) -> bool:
    stored_hash = payload.get("log_sha256")
    if not isinstance(stored_hash, str):
        return False
    unsigned_payload = {
        key: value for key, value in payload.items() if key != "log_sha256"
    }
    return stored_hash == sha256_hex(unsigned_payload)


def write_warning(warning: dict[str, Any], output_dir: Path) -> Path:
    """Write one distance warning with its SHA-256 field to JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    warning_path = output_dir / f"{warning['warning_id']}.json"
    warning_path.write_text(
        json.dumps(warning, ensure_ascii=True, indent=2),
        encoding="utf-8",
    )
    return warning_path