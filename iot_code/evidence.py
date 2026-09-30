"""Versioned off-chain evidence envelope and durable submission outbox."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

EVIDENCE_SCHEMA = "sonarchain.evidence.v1"


def canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def evidence_digest(payload: dict[str, Any]) -> str:
    unsigned = {key: value for key, value in payload.items() if key not in {"evidence_hash", "evidence_status", "tx_hash"}}
    return hashlib.sha256(canonical_json(unsigned)).hexdigest()


def build_evidence(*, event_id: str, device_id: str, sensor_id: str, measured_at: str,
                   received_at: str | None, distance_cm: float | None, severity: str,
                   emergency_stop: bool, confidence: float, policy_version: str = "thresholds.v1",
                   model_version: str = "none", source: str = "gateway") -> dict[str, Any]:
    if not event_id or not device_id or not sensor_id:
        raise ValueError("event_id, device_id and sensor_id are required")
    if distance_cm is not None and (not isinstance(distance_cm, (int, float)) or distance_cm < 0):
        raise ValueError("distance_cm must be non-negative or null")
    if severity not in {"SAFE", "WARNING", "DANGER", "EMERGENCY", "SENSOR_FAULT"}:
        raise ValueError("unsupported severity")
    if emergency_stop and severity not in {"DANGER", "EMERGENCY"}:
        raise ValueError("emergency_stop requires DANGER or EMERGENCY")
    envelope = {
        "schema": EVIDENCE_SCHEMA,
        "event_id": event_id,
        "device_id": device_id,
        "sensor_id": sensor_id,
        "measured_at": measured_at,
        "received_at": received_at or datetime.now(timezone.utc).isoformat(),
        "distance_cm": distance_cm,
        "severity": severity,
        "emergency_stop": bool(emergency_stop),
        "confidence": float(confidence),
        "policy_version": policy_version,
        "model_version": model_version,
        "source": source,
    }
    envelope["evidence_hash"] = evidence_digest(envelope)
    envelope["evidence_status"] = "queued"
    return envelope


@dataclass
class EvidenceOutbox:
    root: Path

    def _path(self, evidence_hash: str) -> Path:
        return self.root / f"{evidence_hash}.json"

    def path_for(self, evidence_hash: str) -> Path:
        return self._path(evidence_hash)

    def enqueue(self, evidence: dict[str, Any]) -> Path:
        expected = evidence_digest(evidence)
        if evidence.get("evidence_hash") != expected:
            raise ValueError("evidence_hash does not match envelope")
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path(expected)
        if path.exists():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if evidence_digest(existing) != expected:
                raise ValueError("evidence collision or tampering detected")
            return path
        path.write_text(json.dumps(evidence, ensure_ascii=True, indent=2), encoding="utf-8")
        return path

    def verify(self, path: Path) -> dict[str, Any]:
        evidence = json.loads(path.read_text(encoding="utf-8"))
        if evidence.get("evidence_hash") != evidence_digest(evidence):
            raise ValueError(f"tampered evidence: {path}")
        return evidence

    def pending(self) -> list[Path]:
        return [path for path in sorted(self.root.glob("*.json")) if self.verify(path).get("evidence_status") != "confirmed"]

    def submit(self, path: Path, submitter: Callable[[dict[str, Any]], str]) -> str:
        evidence = self.verify(path)
        tx_hash = submitter(evidence)
        evidence["tx_hash"] = tx_hash
        evidence["evidence_status"] = "confirmed"
        path.write_text(json.dumps(evidence, ensure_ascii=True, indent=2), encoding="utf-8")
        return tx_hash
