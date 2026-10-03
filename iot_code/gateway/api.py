"""HTTP API and WebSocket bridge from gateway SQLite to the dashboard."""
from __future__ import annotations

import argparse
import asyncio
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SonarChain Gateway API", version="1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_database_path = Path("data/telemetry.db")


def configure_database(path: str | Path) -> None:
    global _database_path
    _database_path = Path(path)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    result["emergency_stop"] = bool(result["emergency_stop"])
    return result


def _read_rows(limit: int = 100, severity: str | None = None) -> list[dict[str, Any]]:
    if not _database_path.exists():
        return []
    with sqlite3.connect(_database_path) as connection:
        connection.row_factory = sqlite3.Row
        query = (
            "SELECT id, event_id, device_id, sensor_id, measured_at, received_at, "
            "distance_cm, severity, emergency_stop, confidence, evidence_hash, "
            "evidence_status, tx_hash, raw_payload FROM telemetry"
        )
        parameters: list[Any] = []
        if severity:
            query += " WHERE severity = ?"
            parameters.append(severity.upper())
        query += " ORDER BY id DESC LIMIT ?"
        parameters.append(max(1, min(limit, 500)))
        rows = connection.execute(query, parameters).fetchall()
    return [_row_to_dict(row) for row in rows]


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"ok": True, "database": str(_database_path), "database_exists": _database_path.exists()}


@app.get("/api/telemetry/latest")
def latest() -> dict[str, Any]:
    rows = _read_rows(1)
    return {"telemetry": rows[0] if rows else None}


@app.get("/api/telemetry/history")
def history(limit: int = 100, severity: str | None = None) -> dict[str, Any]:
    return {"telemetry": _read_rows(limit, severity)}


@app.websocket("/ws/telemetry")
async def telemetry_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    last_id: int | None = None
    try:
        while True:
            rows = _read_rows(1, "EMERGENCY")
            if rows and rows[0]["id"] != last_id:
                last_id = rows[0]["id"]
                await websocket.send_json(rows[0])
            await asyncio.sleep(0.5)
    except (WebSocketDisconnect, RuntimeError):
        return


def main() -> None:
    parser = argparse.ArgumentParser(description="SonarChain gateway HTTP/WebSocket API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--database", default="data/telemetry.db")
    args = parser.parse_args()
    configure_database(args.database)
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
