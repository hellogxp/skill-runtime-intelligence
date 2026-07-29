"""Fail-open local event delivery and durable queue replay."""

import fcntl
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .redaction import redact, redacted_json


DEFAULT_COLLECTOR_ENDPOINT = "http://127.0.0.1:4317/api/events"


def default_state_root() -> Path:
    configured = os.environ.get("SKILL_RUNTIME_HOME")
    return (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".skill-runtime"
    )


def default_event_queue() -> Path:
    return default_state_root() / "queue" / "events.jsonl"


def _secure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass


def append_event_queue(path: Path, envelopes: Iterable[Dict[str, Any]]) -> int:
    """Append redacted envelopes under an exclusive file lock."""
    path = path.expanduser()
    _secure_parent(path)
    written = 0
    with path.open("a+", encoding="utf-8") as handle:
        try:
            path.chmod(0o600)
        except OSError:
            pass
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0, os.SEEK_END)
            for envelope in envelopes:
                handle.write(redacted_json(envelope) + "\n")
                written += 1
            handle.flush()
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    return written


def send_events(
    endpoint: str,
    envelopes: List[Dict[str, Any]],
    timeout_seconds: float = 0.15,
) -> bool:
    if not envelopes:
        return True
    body = json.dumps(redact(envelopes), ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=max(0.01, timeout_seconds)) as response:
            response.read(4096)
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError, OSError):
        return False


def deliver_or_queue(
    envelopes: List[Dict[str, Any]],
    endpoint: str = DEFAULT_COLLECTOR_ENDPOINT,
    queue_path: Optional[Path] = None,
    timeout_seconds: float = 0.15,
) -> str:
    """Deliver immediately or append locally without surfacing a failure."""
    if not envelopes:
        return "ignored"
    if send_events(endpoint, envelopes, timeout_seconds):
        return "delivered"
    append_event_queue(queue_path or default_event_queue(), envelopes)
    return "queued"


def _append_rejected(path: Path, records: List[Dict[str, Any]]) -> None:
    if not records:
        return
    append_event_queue(path, records)


def drain_event_queue(
    database: Path,
    queue_path: Optional[Path] = None,
    max_batch: int = 500,
) -> Dict[str, int]:
    """Replay one bounded queue batch into SQLite.

    The queue lock remains held until the SQLite transaction commits. Hooks may
    wait for this short critical section, but they never depend on replay
    success and never receive a failure from it.
    """
    from .collector import CollectorValidationError, normalize_collector_envelope
    from .storage import Storage

    path = (queue_path or default_event_queue()).expanduser()
    result = {"accepted": 0, "duplicates": 0, "rejected": 0, "remaining": 0}
    if not path.exists():
        return result
    _secure_parent(path)
    rejected_records: List[Dict[str, Any]] = []
    with path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            handle.seek(0)
            lines = handle.readlines()
            selected = lines[:max(1, max_batch)]
            remaining = lines[len(selected):]
            bundles = []
            for line_number, line in enumerate(selected, 1):
                if not line.strip():
                    continue
                try:
                    envelope = json.loads(line)
                    bundles.append(normalize_collector_envelope(envelope))
                except (
                    CollectorValidationError,
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                ) as exc:
                    rejected_records.append(
                        {
                            "rejected_at": time.time(),
                            "line_number": line_number,
                            "error": str(exc),
                        }
                    )
            if bundles:
                storage = Storage(database)
                try:
                    stored = storage.append_collector_events(bundles)
                finally:
                    storage.close()
                result["accepted"] = stored["accepted"]
                result["duplicates"] = stored["duplicates"]
            handle.seek(0)
            handle.truncate()
            handle.writelines(remaining)
            handle.flush()
            result["rejected"] = len(rejected_records)
            result["remaining"] = len(remaining)
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    _append_rejected(path.with_name("rejected.jsonl"), rejected_records)
    return result


def watch_event_queue(
    database: Path,
    queue_path: Optional[Path] = None,
    interval_seconds: float = 1.0,
) -> None:
    import sqlite3

    while True:
        try:
            drain_event_queue(database, queue_path)
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            pass
        time.sleep(max(0.25, interval_seconds))
