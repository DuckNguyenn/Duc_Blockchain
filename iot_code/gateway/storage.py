"""Local SQLite storage for gateway telemetry and evidence submissions."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


class TelemetryStore:
    """Persist gateway observations locally, independently of blockchain availability."""

    def __init__(self, path: str | Path = "data/telemetry.db"):
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT NOT NULL UNIQUE,
                device_id TEXT NOT NULL,
                sensor_id TEXT NOT NULL,
                measured_at TEXT NOT NULL,
                received_at TEXT NOT NULL,
                distance_cm REAL,
                severity TEXT NOT NULL,
                emergency_stop INTEGER NOT NULL,
                confidence REAL NOT NULL,
                evidence_hash TEXT NOT NULL,
                evidence_status TEXT NOT NULL,
                tx_hash TEXT,
                raw_payload TEXT
            )
            """
        )
        self.connection.commit()

    def save(self, result: dict[str, Any], evidence: dict[str, Any], raw_payload: str | None = None) -> None:
        self.connection.execute(
            """
            INSERT INTO telemetry (
                event_id, device_id, sensor_id, measured_at, received_at,
                distance_cm, severity, emergency_stop, confidence,
                evidence_hash, evidence_status, tx_hash, raw_payload
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(event_id) DO UPDATE SET
                evidence_status = excluded.evidence_status,
                tx_hash = excluded.tx_hash
            """ ,
            (
                result["event_id"],
                result["device_id"],
                evidence["sensor_id"],
                evidence["measured_at"],
                evidence["received_at"],
                result.get("distance_cm"),
                result["severity"],
                int(result["emergency_stop"]),
                result["confidence"],
                result["evidence_hash"],
                result.get("submission_status", evidence.get("evidence_status", "queued")),
                result.get("tx_hash"),
                raw_payload,
            ),
        )
        self.connection.commit()

    def mark_confirmed(self, event_id: str, tx_hash: str) -> None:
        self.connection.execute(
            "UPDATE telemetry SET evidence_status = 'confirmed', tx_hash = ? WHERE event_id = ?",
            (tx_hash, event_id),
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "TelemetryStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
