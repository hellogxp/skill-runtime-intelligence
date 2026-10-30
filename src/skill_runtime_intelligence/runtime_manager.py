"""Safe lifecycle management for the local Skill Runtime process."""

import json
import os
import shlex
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from .event_queue import default_state_root


RUNTIME_STATE_VERSION = "skill-runtime-process-v1"
_MANAGED_CHILDREN: Dict[int, subprocess.Popen] = {}


def runtime_pid_path(state_root: Optional[Path] = None) -> Path:
    return (state_root or default_state_root()) / "run" / "runtime.json"


def runtime_log_path(state_root: Optional[Path] = None) -> Path:
    return (state_root or default_state_root()) / "logs" / "runtime.log"


def _atomic_write(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(value, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        temporary.chmod(0o600)
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def _read_record(state_root: Optional[Path] = None) -> Dict[str, Any]:
    path = runtime_pid_path(state_root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _process_alive(pid: int) -> bool:
    if pid <= 1:
        return False
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _process_command(pid: int) -> str:
    try:
        result = subprocess.run(
            # BSD ps (including macOS) truncates long command lines to the
            # current display width unless ``-ww`` is requested. Runtime
            # commands intentionally include explicit database, config,
            # queue, and socket paths, so a truncated command cannot be used
            # for safe ownership verification.
            ["ps", "-ww", "-p", str(pid), "-o", "command="],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
            text=True,
            timeout=2,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _managed_process(record: Dict[str, Any]) -> bool:
    if (
        record.get("version") != RUNTIME_STATE_VERSION
        or record.get("marker") != "skill-runtime-intelligence"
    ):
        return False
    pid = int(record.get("pid") or 0)
    if not _process_alive(pid):
        return False
    recorded = record.get("command")
    if not isinstance(recorded, list) or not recorded:
        return False
    try:
        actual = shlex.split(_process_command(pid))
    except ValueError:
        return False
    if "start" not in actual or "--foreground" not in actual:
        return False
    if len(recorded) >= 3 and recorded[1:3] == ["-m", "skill_runtime_intelligence"]:
        # macOS framework builds can report the underlying ``Python`` binary
        # in ps while ``sys.executable`` records the toolcache shim.  The
        # interpreter spelling is therefore not a stable identity boundary.
        # Every module and runtime argument after it remains an exact match,
        # including the unique state, database, queue, socket, and port paths.
        return actual[1:] == [str(token) for token in recorded[1:]]
    expected_launcher = Path(str(recorded[0])).expanduser().resolve()
    for token in actual:
        if not token.startswith(("/", ".")):
            continue
        try:
            if Path(token).expanduser().resolve() == expected_launcher:
                return True
        except OSError:
            continue
    return False


def health_url(host: str, port: int) -> str:
    target = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    return f"http://{target}:{port}/api/health"


def _command_argument(command: Any, name: str) -> str:
    if not isinstance(command, list):
        return ""
    try:
        index = command.index(name)
        return str(command[index + 1])
    except (ValueError, IndexError):
        return ""


def fetch_health(host: str, port: int, timeout: float = 0.4) -> Dict[str, Any]:
    try:
        with urlopen(health_url(host, port), timeout=timeout) as response:
            value = json.loads(response.read(1024 * 1024))
            if 200 <= response.status < 300 and isinstance(value, dict):
                return value
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        pass
    return {}


def runtime_status(
    state_root: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 4317,
) -> Dict[str, Any]:
    record = _read_record(state_root)
    pid = int(record.get("pid") or 0)
    managed_alive = _managed_process(record)
    health = fetch_health(host, port)
    product_healthy = bool(
        health.get("ok")
        and health.get("product") == "skill-runtime-intelligence"
    )
    management_mode = (
        "managed"
        if managed_alive and product_healthy
        else "external"
        if product_healthy
        else "none"
    )
    return {
        "running": product_healthy,
        "process_alive": managed_alive,
        "collector_healthy": product_healthy,
        "managed": bool(managed_alive and product_healthy),
        "management_mode": management_mode,
        "pid": pid if managed_alive else None,
        "url": health_url(host, port).removesuffix("/api/health"),
        "state_path": str(runtime_pid_path(state_root)),
        "log_path": str(runtime_log_path(state_root)),
        "started_at": record.get("started_at"),
        "database": (
            _command_argument(record.get("command"), "--database")
            if managed_alive
            else ""
        ),
        "config_path": (
            _command_argument(record.get("command"), "--config")
            if managed_alive
            else ""
        ),
        "health": health,
    }


def start_runtime(
    command: List[str],
    *,
    state_root: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 4317,
    wait_seconds: float = 75.0,
) -> Dict[str, Any]:
    existing = runtime_status(state_root, host, port)
    if existing["running"]:
        return {**existing, "changed": False, "reason": "already_running"}
    if existing["process_alive"]:
        raise RuntimeError(
            "a managed process exists but its Collector is unhealthy; "
            "run `skill-runtime stop` before retrying"
        )

    log_path = runtime_log_path(state_root)
    log_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with log_path.open("ab", buffering=0) as output:
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=output,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )
    _MANAGED_CHILDREN[process.pid] = process
    record = {
        "version": RUNTIME_STATE_VERSION,
        "pid": process.pid,
        "marker": "skill-runtime-intelligence",
        "command": command,
        "host": host,
        "port": port,
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write(runtime_pid_path(state_root), record)

    deadline = time.monotonic() + max(0.5, wait_seconds)
    while time.monotonic() < deadline:
        health = fetch_health(host, port)
        if (
            health.get("ok")
            and health.get("product") == "skill-runtime-intelligence"
        ):
            status = runtime_status(state_root, host, port)
            if status["running"]:
                return {
                    **status,
                    "changed": True,
                    "reason": "started",
                }
        if process.poll() is not None:
            break
        time.sleep(0.1)

    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    _MANAGED_CHILDREN.pop(process.pid, None)
    runtime_pid_path(state_root).unlink(missing_ok=True)
    detail = ""
    try:
        detail = "\n".join(
            log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-12:]
        )
    except OSError:
        pass
    raise RuntimeError(
        "Skill Runtime did not become healthy"
        + (f":\n{detail}" if detail else "")
    )


def stop_runtime(
    state_root: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 4317,
    wait_seconds: float = 8.0,
) -> Dict[str, Any]:
    record = _read_record(state_root)
    record_host = str(record.get("host") or host)
    try:
        record_port = int(record.get("port") or port)
    except (TypeError, ValueError):
        record_port = port
    path = runtime_pid_path(state_root)
    pid = int(record.get("pid") or 0)
    if not pid or not _process_alive(pid):
        path.unlink(missing_ok=True)
        return {
            **runtime_status(state_root, record_host, record_port),
            "changed": False,
            "reason": "not_running",
        }
    if not _managed_process(record):
        raise RuntimeError(
            f"refusing to stop PID {pid}: it is not a verified Skill Runtime process"
        )

    os.kill(pid, signal.SIGTERM)
    child = _MANAGED_CHILDREN.get(pid)
    deadline = time.monotonic() + max(0.5, wait_seconds)
    while time.monotonic() < deadline and _process_alive(pid):
        if child is not None and child.poll() is not None:
            break
        time.sleep(0.1)
    if _process_alive(pid) and not (child is not None and child.poll() is not None):
        os.kill(pid, signal.SIGKILL)
    if child is not None:
        try:
            child.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass
        _MANAGED_CHILDREN.pop(pid, None)
    path.unlink(missing_ok=True)
    return {
        **runtime_status(state_root, record_host, record_port),
        "changed": True,
        "reason": "stopped",
    }


def restart_runtime(
    state_root: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 4317,
) -> Dict[str, Any]:
    """Restart only a verified managed Runtime with its exact arguments."""
    record = _read_record(state_root)
    if not _managed_process(record):
        raise RuntimeError(
            "no verified managed Skill Runtime is running; use `skill-runtime start`"
        )
    command = record.get("command")
    if not isinstance(command, list) or not command:
        raise RuntimeError("managed Skill Runtime command is unavailable")
    record_host = str(record.get("host") or host)
    try:
        record_port = int(record.get("port") or port)
    except (TypeError, ValueError):
        record_port = port
    preserved_command = [str(token) for token in command]
    stop_runtime(state_root, record_host, record_port)
    return start_runtime(
        preserved_command,
        state_root=state_root,
        host=record_host,
        port=record_port,
    )
