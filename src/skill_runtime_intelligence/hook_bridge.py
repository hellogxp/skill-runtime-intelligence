"""Low-latency, local-only bridge for Agent hook payloads.

The normal fast path sends a hook payload over a permission-restricted Unix
socket to the already-running Skill Runtime process.  The hook command falls
back to the standalone fail-open queue writer when the socket is unavailable.
Raw hook payloads are never written to disk by this bridge.
"""

import json
import os
import socket
import sqlite3
import stat
import threading
import queue
from pathlib import Path
from typing import Optional

from .collector import normalize_collector_payload
from .event_queue import append_event_queue, default_event_queue, default_state_root
from .hook_adapter import (
    HOOK_EVENT_TYPES,
    SUPPORTED_HOOK_AGENTS,
    build_hook_envelopes,
)
from .storage import Storage


MAX_HOOK_INPUT_BYTES = 1024 * 1024
MAX_HEADER_BYTES = 512


def default_hook_socket() -> Path:
    return default_state_root() / "run" / "hook.sock"


class HookBridge:
    """Receive raw local hook payloads and persist normalized evidence."""

    def __init__(
        self,
        database: Path,
        socket_path: Optional[Path] = None,
        queue_path: Optional[Path] = None,
    ):
        self.database = database.expanduser().resolve()
        self.socket_path = (socket_path or default_hook_socket()).expanduser()
        self.queue_path = (queue_path or default_event_queue()).expanduser()
        self._socket: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._ingest_thread: Optional[threading.Thread] = None
        self._pending = queue.Queue()
        self._active_skills = {}
        self._stop = threading.Event()
        self._socket_inode: Optional[int] = None

    def start(self) -> "HookBridge":
        if self._thread and self._thread.is_alive():
            return self
        # Initialize the schema and WAL mode before accepting clients.  Doing
        # this in the ingest thread races observers that open Storage as soon
        # as a native sender returns, and both connections can attempt the
        # journal-mode transition at once.
        storage = Storage(self.database)
        storage.close()
        self.socket_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.socket_path.parent.chmod(0o700)
        except OSError:
            pass
        if self.socket_path.exists() or self.socket_path.is_symlink():
            metadata = self.socket_path.lstat()
            if not stat.S_ISSOCK(metadata.st_mode):
                raise RuntimeError(
                    f"refusing to replace non-socket hook bridge path: {self.socket_path}"
                )
            self.socket_path.unlink()

        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            listener.bind(str(self.socket_path))
            os.chmod(self.socket_path, 0o600)
            listener.listen(32)
            listener.settimeout(0.5)
        except Exception:
            listener.close()
            if self.socket_path.exists():
                self.socket_path.unlink()
            raise
        self._socket = listener
        self._socket_inode = self.socket_path.lstat().st_ino
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._serve,
            daemon=True,
            name="skill-runtime-hook-bridge",
        )
        self._ingest_thread = threading.Thread(
            target=self._ingest,
            daemon=True,
            name="skill-runtime-hook-ingest",
        )
        self._ingest_thread.start()
        self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        listener = self._socket
        self._socket = None
        if listener is not None:
            listener.close()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        if self._ingest_thread and self._ingest_thread.is_alive():
            self._ingest_thread.join(timeout=2.0)
        self._ingest_thread = None
        try:
            metadata = self.socket_path.lstat()
            if (
                stat.S_ISSOCK(metadata.st_mode)
                and metadata.st_ino == self._socket_inode
            ):
                self.socket_path.unlink()
        except FileNotFoundError:
            pass

    def _serve(self) -> None:
        while not self._stop.is_set():
            listener = self._socket
            if listener is None:
                return
            try:
                connection, _ = listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            self._handle(connection)

    def _handle(self, connection: socket.socket) -> None:
        try:
            connection.settimeout(0.5)
            raw = bytearray()
            while len(raw) <= MAX_HOOK_INPUT_BYTES + MAX_HEADER_BYTES:
                chunk = connection.recv(65536)
                if not chunk:
                    break
                raw.extend(chunk)
            connection.close()
            header_bytes, separator, payload_bytes = bytes(raw).partition(b"\n")
            if (
                not separator
                or not header_bytes
                or len(header_bytes) > MAX_HEADER_BYTES
                or not payload_bytes
                or len(payload_bytes) > MAX_HOOK_INPUT_BYTES
            ):
                return
            self._pending.put((header_bytes, payload_bytes))
        except (
            OSError,
        ):
            return
        finally:
            connection.close()

    def _ingest(self) -> None:
        while not self._stop.is_set() or not self._pending.empty():
            try:
                first = self._pending.get(timeout=0.1)
            except queue.Empty:
                continue
            pending = [first]
            while len(pending) < 64:
                try:
                    pending.append(self._pending.get_nowait())
                except queue.Empty:
                    break
            all_bundles = []
            all_envelopes = []
            for header_bytes, payload_bytes in pending:
                envelopes = []
                try:
                    header = json.loads(header_bytes)
                    agent = str(header.get("agent") or "codex")
                    event = str(header.get("event") or "")
                    if (
                        agent not in SUPPORTED_HOOK_AGENTS
                        or event not in HOOK_EVENT_TYPES
                    ):
                        raise ValueError("unsupported hook header")
                    payload = json.loads(payload_bytes)
                    envelopes = build_hook_envelopes(agent, event, payload)
                    if not envelopes:
                        raise ValueError("hook event produced no evidence")
                    session_id = str(payload.get("session_id") or "")
                    turn_id = str(payload.get("turn_id") or "")
                    active_key = (agent, session_id, turn_id)
                    active = self._active_skills.get(active_key)
                    if active:
                        for envelope in envelopes:
                            if not envelope.get("skill"):
                                envelope["skill"] = dict(active["skill"])
                                envelope["skill_run_id"] = active["skill_run_id"]
                                envelope["activation_mode"] = active["activation_mode"]
                    bundles = normalize_collector_payload(envelopes)
                    for bundle in bundles:
                        if (
                            bundle.get("event", {}).get("event_type")
                            == "skill.activated"
                        ):
                            run = bundle.get("skill_run")
                            skill = bundle.get("skill")
                            if run and skill:
                                self._active_skills[active_key] = {
                                    "skill": {
                                        "name": skill["name"],
                                        "source_path": skill["source_path"],
                                        "digest": skill["digest"],
                                    },
                                    "skill_run_id": run["skill_run_id"],
                                    "activation_mode": run["activation_mode"],
                                }
                    all_bundles.extend(bundles)
                    all_envelopes.extend(envelopes)
                    if event in {"Stop", "SessionEnd"}:
                        if event == "SessionEnd":
                            for key in list(self._active_skills):
                                if key[0] == agent and key[1] == session_id:
                                    self._active_skills.pop(key, None)
                        else:
                            self._active_skills.pop(active_key, None)
                except (
                    json.JSONDecodeError,
                    UnicodeDecodeError,
                    ValueError,
                ):
                    try:
                        if envelopes:
                            append_event_queue(self.queue_path, envelopes)
                    except (OSError, ValueError):
                        pass
                self._pending.task_done()
            if not all_bundles:
                continue
            try:
                storage = Storage(self.database)
                try:
                    storage.append_collector_events(all_bundles)
                finally:
                    storage.close()
            except (OSError, sqlite3.Error, ValueError):
                try:
                    append_event_queue(self.queue_path, all_envelopes)
                except (OSError, ValueError):
                    pass

    def __enter__(self) -> "HookBridge":
        return self.start()

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()
