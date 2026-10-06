"""Submit evidence in order without making Serial wait for chain receipts."""
from __future__ import annotations

import json
import threading
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any, Callable

from iot_code.evidence import EvidenceOutbox
from iot_code.gateway.storage import TelemetryStore

_output_lock = threading.Lock()


def emit_result(result: dict[str, Any]) -> None:
    with _output_lock:
        print(json.dumps(result, ensure_ascii=False), flush=True)


class ChainSubmissionWorker:
    def __init__(self, outbox: EvidenceOutbox, database: str, submitter: Callable | None):
        self.outbox = outbox
        self.database = database
        self.submitter = submitter
        self.queue: Queue[Path] = Queue(maxsize=256)
        self.stopping = threading.Event()
        self.thread: threading.Thread | None = None

    def enqueue(self, path: Path) -> None:
        try:
            self.queue.put_nowait(path)
        except Full:
            # The durable queued evidence remains available for --retry-outbox.
            emit_result({"evidence_hash": path.stem, "submission_status": "queued",
                         "submission_error": "Chain queue full; retry the durable outbox later."})

    def _run(self) -> None:
        while not self.stopping.is_set():
            try:
                path = self.queue.get(timeout=0.2)
            except Empty:
                continue
            result = {"evidence_hash": path.stem}
            try:
                evidence = self.outbox.verify(path)
                result["event_id"] = evidence["event_id"]
                tx_hash = self.outbox.submit(path, self.submitter)
                # SQLite connections stay on the thread that created them.
                with TelemetryStore(self.database) as store:
                    store.mark_confirmed(evidence["event_id"], tx_hash)
                result.update(submission_status="confirmed", tx_hash=tx_hash)
            except Exception as error:
                result.update(submission_status="pending", submission_error=str(error))
                if "event_id" in result:
                    try:
                        self.outbox.mark_pending(path)
                        with TelemetryStore(self.database) as store:
                            store.mark_pending(result["event_id"])
                    except Exception as persistence_error:
                        result["persistence_error"] = str(persistence_error)
            finally:
                emit_result(result)
                self.queue.task_done()

    def __enter__(self) -> "ChainSubmissionWorker":
        if self.submitter is not None:
            self.thread = threading.Thread(target=self._run, name="chain-submissions", daemon=True)
            self.thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self.stopping.set()
        if self.thread is not None:
            self.thread.join(timeout=1)
