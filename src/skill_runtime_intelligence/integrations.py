"""Safe planning, installation, and removal for Agent hook integrations."""

import json
import os
import shlex
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from .event_queue import default_event_queue, default_state_root
from .hook_bridge import default_hook_socket
from .native_sender import native_hook_sender_path


INTEGRATION_MARKER = "skill-runtime-intelligence"
MANAGED_CODEX_EVENTS = {
    "SessionStart": "startup|resume|clear|compact",
    "SessionEnd": "*",
    "UserPromptSubmit": "*",
    "PreToolUse": "*",
    "PostToolUse": "*",
    "PreCompact": "*",
    "PostCompact": "*",
    "SubagentStart": "*",
    "SubagentStop": "*",
    "Stop": "*",
}
MANAGED_CLAUDE_EVENTS = {
    "SessionStart": "startup|resume|clear|compact",
    "SessionEnd": "*",
    "UserPromptSubmit": "*",
    "UserPromptExpansion": "*",
    "PreToolUse": "*",
    "PostToolUse": "*",
    "PostToolUseFailure": "*",
    "Stop": "*",
    "InstructionsLoaded": "*",
    "SubagentStart": "*",
    "SubagentStop": "*",
}


class IntegrationError(ValueError):
    pass


@lru_cache(maxsize=8)
def _latest_codex_session_version() -> str:
    root = Path.home() / ".codex" / "sessions"
    try:
        candidates = list(root.rglob("*.jsonl"))
        latest = max(candidates, key=lambda path: path.stat().st_mtime)
        with latest.open(encoding="utf-8") as source:
            for _ in range(8):
                line = source.readline()
                if not line:
                    break
                record = json.loads(line)
                if record.get("type") == "session_meta":
                    return str(record.get("payload", {}).get("cli_version") or "")[:160]
    except (OSError, ValueError, json.JSONDecodeError):
        return ""
    return ""


@lru_cache(maxsize=8)
def _detect_cli_version(command: str) -> Dict[str, Any]:
    executable = shutil.which(command)
    session_version = _latest_codex_session_version() if command == "codex" else ""
    if not executable and not session_version:
        return {
            "cli_path": "",
            "agent_version": "",
            "version_status": "not_installed",
            "version_source": "none",
        }
    return {
        "cli_path": executable or "",
        "agent_version": session_version,
        "version_status": "observed" if session_version else "unavailable",
        "version_source": (
            "local_session_metadata" if session_version else "executable_presence"
        ),
    }


def default_codex_hooks_path() -> Path:
    return Path.home() / ".codex" / "hooks.json"


def default_claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _load_hooks(path: Path, agent_label: str = "Agent") -> Dict[str, Any]:
    if not path.exists():
        return {"hooks": {}}
    if path.is_symlink():
        raise IntegrationError(f"refusing to replace symlinked config: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise IntegrationError(
            f"unable to parse {agent_label} hooks config: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise IntegrationError(f"{agent_label} hooks config must be a JSON object")
    hooks = value.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise IntegrationError(
            f"{agent_label} hooks config field `hooks` must be an object"
        )
    return value


def _is_managed_command(command: Any, agent: Optional[str] = None) -> bool:
    text = str(command or "")
    if f"--managed-by {INTEGRATION_MARKER}" not in text:
        return False
    if agent and f"--agent {agent}" not in text:
        return False
    return " hook --agent " in f" {text} " or "skill-runtime-hook" in text


def _managed_events(config: Dict[str, Any], agent: str = "codex") -> List[str]:
    found = []
    for event, groups in config.get("hooks", {}).items():
        if not isinstance(groups, list):
            continue
        if any(
            _is_managed_command(hook.get("command"), agent)
            for group in groups
            if isinstance(group, dict)
            for hook in group.get("hooks", [])
            if isinstance(hook, dict)
        ):
            found.append(event)
    return sorted(found)


def inspect_codex_integration(
    config_path: Optional[Path] = None,
    executable: str = "",
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_codex_hooks_path()).expanduser()
    config = _load_hooks(path, "Codex")
    installed_events = _managed_events(config, "codex")
    cli = _detect_cli_version("codex")
    return {
        "agent": "codex",
        "detected": (Path.home() / ".codex").is_dir(),
        "config_path": str(path),
        "config_exists": path.exists(),
        "config_valid": True,
        "executable": executable,
        "installed": bool(installed_events),
        **cli,
        "installed_events": installed_events,
        "planned_events": sorted(MANAGED_CODEX_EVENTS),
        "collection_mode": "official_hook",
        "selected_collection_mode": (
            "official_hook" if installed_events else "transcript_fallback"
        ),
        "available_collection_modes": [
            "official_hook",
            "transcript_fallback",
            "observability_import",
        ],
        "native_skill_telemetry": "not_detected",
        "fail_open": True,
        "collector_endpoint": "http://127.0.0.1:4317/api/events",
        "fast_path": "unix_socket",
        "hook_socket": str(default_hook_socket()),
        "hook_socket_active": default_hook_socket().is_socket(),
        "native_sender": str(native_hook_sender_path(state_root)),
        "native_sender_available": native_hook_sender_path(state_root).is_file(),
        "offline_queue": str(default_event_queue()),
        "paths_read": [
            str(Path.home() / ".codex" / "sessions"),
            str(Path.home() / ".codex" / "skills"),
            str(path),
        ],
        "changes_without_consent": [],
    }


def inspect_claude_integration(
    config_path: Optional[Path] = None,
    executable: str = "",
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_claude_settings_path()).expanduser()
    config = _load_hooks(path, "Claude Code")
    installed_events = _managed_events(config, "claude-code")
    cli = _detect_cli_version("claude")
    return {
        "agent": "claude-code",
        "detected": (Path.home() / ".claude").is_dir()
        or bool(shutil.which("claude")),
        "config_path": str(path),
        "config_exists": path.exists(),
        "config_valid": True,
        "executable": executable,
        "installed": bool(installed_events),
        **cli,
        "installed_events": installed_events,
        "planned_events": sorted(MANAGED_CLAUDE_EVENTS),
        "available_unmanaged_events": ["FileChanged"],
        "collection_mode": "official_hook",
        "selected_collection_mode": (
            "official_hook" if installed_events else "not_configured"
        ),
        "available_collection_modes": [
            "official_hook",
            "observability_import",
        ],
        "native_skill_telemetry": "not_detected",
        "fail_open": True,
        "async": True,
        "collector_endpoint": "http://127.0.0.1:4317/api/events",
        "fast_path": "unix_socket",
        "hook_socket": str(default_hook_socket()),
        "hook_socket_active": default_hook_socket().is_socket(),
        "native_sender": str(native_hook_sender_path(state_root)),
        "native_sender_available": native_hook_sender_path(state_root).is_file(),
        "offline_queue": str(default_event_queue()),
        "paths_read": [
            str(Path.home() / ".claude" / "projects"),
            str(Path.home() / ".claude" / "skills"),
            str(path),
        ],
        "changes_without_consent": [],
        "note": (
            "FileChanged is supported when emitted, but is not installed with a "
            "global wildcard because Claude Code watch paths are literal filenames."
        ),
    }


def _atomic_write_json(path: Path, value: Dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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
        temporary.chmod(mode)
        os.replace(str(temporary), str(path))
    finally:
        if temporary.exists():
            temporary.unlink()


def _backup(path: Path) -> Optional[Path]:
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = path.with_name(f"{path.name}.skill-runtime.bak.{timestamp}")
    shutil.copy2(path, backup)
    return backup


def _hook_command(
    executable: str,
    event: str,
    agent: str = "codex",
    state_root: Optional[Path] = None,
) -> str:
    executable_path = Path(executable).expanduser()
    fast_hook = executable_path.with_name("skill-runtime-hook")
    fallback = " ".join(
        (
            shlex.quote(str(fast_hook)) if fast_hook.is_file() else shlex.quote(executable),
            *(tuple() if fast_hook.is_file() else ("hook",)),
            "--agent",
            agent,
            "--event",
            shlex.quote(event),
            "--managed-by",
            INTEGRATION_MARKER,
        )
    )
    socket_path = default_hook_socket(state_root)
    native_sender = native_hook_sender_path(state_root)
    header = json.dumps({"agent": agent, "event": event}, separators=(",", ":"))
    nc_branch = ""
    if sys.platform != "darwin":
        nc_branch = (
            f"elif [ -S {shlex.quote(str(socket_path))} ] && [ -x /usr/bin/nc ]; then "
            f"{{ printf '%s\\n' {shlex.quote(header)}; cat; }} | "
            f"/usr/bin/nc -N -U -w 1 {shlex.quote(str(socket_path))} "
            f">/dev/null 2>&1 || true; "
        )
    delivery = (
        f"if [ -S {shlex.quote(str(socket_path))} ] && "
        f"[ -x {shlex.quote(str(native_sender))} ]; then "
        f"{shlex.quote(str(native_sender))} --agent {shlex.quote(agent)} "
        f"--event {shlex.quote(event)} --socket {shlex.quote(str(socket_path))} "
        f">/dev/null 2>&1 || true; "
        f"{nc_branch}"
        f"else {fallback} >/dev/null 2>&1 || true; fi"
    )
    # Codex stop hooks require a JSON object on stdout. Returning an empty
    # object preserves the Agent's normal behavior while the sender remains
    # fully fail-open. Other event hooks stay silent.
    if agent == "codex" and event in {"Stop", "SubagentStop"}:
        return f"{delivery}; printf '%s\\n' '{{}}'"
    return delivery


def _enable_hooks(
    *,
    agent: str,
    integration_name: str,
    agent_label: str,
    executable: str,
    path: Path,
    managed_events: Dict[str, str],
    state_root: Optional[Path],
    asynchronous: bool,
) -> Dict[str, Any]:
    if not executable:
        raise IntegrationError("skill-runtime executable path is required")
    config = _load_hooks(path, agent_label)
    hooks = config["hooks"]
    existing = set(_managed_events(config, agent))
    added = []
    for event, matcher in managed_events.items():
        if event in existing:
            continue
        groups = hooks.setdefault(event, [])
        if not isinstance(groups, list):
            raise IntegrationError(f"{agent_label} hook group `{event}` must be a list")
        hook = {
            "type": "command",
            "command": _hook_command(executable, event, agent, state_root),
            "timeout": 2,
        }
        if asynchronous:
            hook["async"] = True
        groups.append({"matcher": matcher, "hooks": [hook]})
        added.append(event)
    if not added:
        return {
            "changed": False,
            "installed_events": sorted(existing),
            "config_path": str(path),
            "backup_path": None,
        }

    backup = _backup(path)
    original_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    _atomic_write_json(path, config, original_mode)
    manifest = {
        "integration": integration_name,
        "managed_by": INTEGRATION_MARKER,
        "config_path": str(path),
        "executable": executable,
        "installed_events": sorted(existing | set(added)),
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "backup_path": str(backup) if backup else None,
        "fail_open": True,
        "async": asynchronous,
    }
    manifest_path = (
        state_root or default_state_root()
    ) / "integrations" / f"{agent}.json"
    _atomic_write_json(manifest_path, manifest)
    return {
        "changed": True,
        "added_events": sorted(added),
        "installed_events": manifest["installed_events"],
        "config_path": str(path),
        "backup_path": str(backup) if backup else None,
        "manifest_path": str(manifest_path),
    }


def enable_codex_hooks(
    executable: str,
    config_path: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_codex_hooks_path()).expanduser()
    return _enable_hooks(
        agent="codex",
        integration_name="codex-hooks",
        agent_label="Codex",
        executable=executable,
        path=path,
        managed_events=MANAGED_CODEX_EVENTS,
        state_root=state_root,
        asynchronous=False,
    )


def enable_claude_hooks(
    executable: str,
    config_path: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_claude_settings_path()).expanduser()
    return _enable_hooks(
        agent="claude-code",
        integration_name="claude-code-hooks",
        agent_label="Claude Code",
        executable=executable,
        path=path,
        managed_events=MANAGED_CLAUDE_EVENTS,
        state_root=state_root,
        asynchronous=True,
    )


def _remove_hooks(
    *,
    agent: str,
    agent_label: str,
    path: Path,
    state_root: Optional[Path],
) -> Dict[str, Any]:
    config = _load_hooks(path, agent_label)
    removed = []
    for event, groups in list(config["hooks"].items()):
        if not isinstance(groups, list):
            continue
        next_groups = []
        for group in groups:
            if not isinstance(group, dict):
                next_groups.append(group)
                continue
            group_hooks = group.get("hooks", [])
            if not isinstance(group_hooks, list):
                next_groups.append(group)
                continue
            kept_hooks = [
                hook
                for hook in group_hooks
                if not (
                    isinstance(hook, dict)
                    and _is_managed_command(hook.get("command"), agent)
                )
            ]
            removed.extend([event] * (len(group_hooks) - len(kept_hooks)))
            if kept_hooks:
                next_group = dict(group)
                next_group["hooks"] = kept_hooks
                next_groups.append(next_group)
        if next_groups:
            config["hooks"][event] = next_groups
        else:
            config["hooks"].pop(event, None)
    if not removed:
        return {
            "changed": False,
            "removed_events": [],
            "config_path": str(path),
            "backup_path": None,
        }

    backup = _backup(path)
    original_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    _atomic_write_json(path, config, original_mode)
    manifest_path = (
        state_root or default_state_root()
    ) / "integrations" / f"{agent}.json"
    if manifest_path.exists():
        manifest_path.unlink()
    return {
        "changed": True,
        "removed_events": sorted(set(removed)),
        "config_path": str(path),
        "backup_path": str(backup) if backup else None,
    }


def remove_codex_hooks(
    config_path: Optional[Path] = None, state_root: Optional[Path] = None
) -> Dict[str, Any]:
    return _remove_hooks(
        agent="codex",
        agent_label="Codex",
        path=(config_path or default_codex_hooks_path()).expanduser(),
        state_root=state_root,
    )


def remove_claude_hooks(
    config_path: Optional[Path] = None, state_root: Optional[Path] = None
) -> Dict[str, Any]:
    return _remove_hooks(
        agent="claude-code",
        agent_label="Claude Code",
        path=(config_path or default_claude_settings_path()).expanduser(),
        state_root=state_root,
    )
