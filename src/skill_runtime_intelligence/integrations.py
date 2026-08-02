"""Safe planning, installation, and removal for Agent hook integrations."""

import json
import os
import shlex
import shutil
import subprocess
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
MANAGED_QODER_EVENTS = {
    "UserPromptSubmit": "",
    "PreToolUse": "",
    "PostToolUse": "",
    "PostToolUseFailure": "",
    "Stop": "",
}
OPENCODE_PLUGIN_MARKER = (
    "// managed-by: skill-runtime-intelligence; adapter: opencode"
)


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
    command_version = ""
    if executable and not session_version:
        try:
            result = subprocess.run(
                [executable, "--version"],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode == 0:
                command_version = " ".join(result.stdout.split())[:160]
        except (OSError, subprocess.SubprocessError):
            command_version = ""
    observed_version = session_version or command_version
    return {
        "cli_path": executable or "",
        "agent_version": observed_version,
        "version_status": "observed" if observed_version else "unavailable",
        "version_source": (
            "local_session_metadata"
            if session_version
            else ("cli_version" if command_version else "executable_presence")
        ),
    }


def default_codex_hooks_path() -> Path:
    return Path.home() / ".codex" / "hooks.json"


def default_claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def default_qoder_settings_path() -> Path:
    return Path.home() / ".qoder" / "settings.json"


def default_opencode_plugin_path() -> Path:
    return (
        Path.home()
        / ".config"
        / "opencode"
        / "plugins"
        / "skill-runtime-intelligence.js"
    )


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


def inspect_qoder_integration(
    config_path: Optional[Path] = None,
    executable: str = "",
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_qoder_settings_path()).expanduser()
    config = _load_hooks(path, "Qoder")
    installed_events = _managed_events(config, "qoder")
    cli = _detect_cli_version("qodercli")
    return {
        "agent": "qoder",
        "detected": (Path.home() / ".qoder").is_dir()
        or bool(shutil.which("qodercli")),
        "config_path": str(path),
        "config_exists": path.exists(),
        "config_valid": True,
        "executable": executable,
        "installed": bool(installed_events),
        **cli,
        "installed_events": installed_events,
        "planned_events": sorted(MANAGED_QODER_EVENTS),
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
        "async": False,
        "collector_endpoint": "http://127.0.0.1:4317/api/events",
        "fast_path": "unix_socket",
        "hook_socket": str(default_hook_socket()),
        "hook_socket_active": default_hook_socket().is_socket(),
        "native_sender": str(native_hook_sender_path(state_root)),
        "native_sender_available": native_hook_sender_path(state_root).is_file(),
        "offline_queue": str(default_event_queue()),
        "paths_read": [
            str(Path.home() / ".qoder" / "skills"),
            str(Path.home() / ".qoder" / "projects"),
            str(path),
        ],
        "changes_without_consent": [],
        "note": (
            "Qoder command hooks are synchronous. Skill Runtime always returns "
            "success and performs only bounded local delivery on the hook path."
        ),
    }


def _opencode_command_parts(
    executable: str,
    state_root: Optional[Path],
) -> Dict[str, Any]:
    native_sender = native_hook_sender_path(state_root)
    fallback = Path(executable).expanduser() if executable else None
    return {
        "native_sender": str(native_sender),
        "fallback_executable": str(fallback) if fallback else "",
        "socket_path": str(default_hook_socket(state_root)),
    }


def _opencode_plugin_source(
    executable: str,
    state_root: Optional[Path] = None,
) -> str:
    paths = _opencode_command_parts(executable, state_root)
    settings = json.dumps(paths, ensure_ascii=True, separators=(",", ":"))
    return f"""{OPENCODE_PLUGIN_MARKER}
import {{ spawn }} from "node:child_process"

const SETTINGS = {settings}
const EVENT_MAP = {{
  "session.created": "SessionStart",
  "session.idle": "Stop",
  "session.error": "SessionError",
  "tool.execute.before": "PreToolUse",
  "tool.execute.after": "PostToolUse",
  "file.edited": "FileChanged",
}}

function first(...values) {{
  for (const value of values) {{
    if (value !== undefined && value !== null && value !== "") return value
  }}
  return ""
}}

function minimalPayload(event, directory) {{
  const p = event && typeof event.properties === "object" ? event.properties : {{}}
  const info = p.info && typeof p.info === "object" ? p.info : {{}}
  const message = p.message && typeof p.message === "object" ? p.message : {{}}
  const part = p.part && typeof p.part === "object" ? p.part : {{}}
  const tool = first(p.tool, part.tool, info.tool)
  const input = first(p.input, p.args, part.input, part.args, {{}})
  const filePath = first(p.file, p.path, p.filePath, input?.filePath, input?.file_path)
  return {{
    session_id: String(first(
      p.sessionID, p.sessionId, p.session_id,
      info.sessionID, info.sessionId, info.id,
      message.sessionID, message.sessionId, part.sessionID
    )),
    turn_id: String(first(p.messageID, p.messageId, message.id, info.id)),
    tool_name: String(tool),
    tool_use_id: String(first(p.callID, p.callId, part.callID, part.id)),
    tool_input: input && typeof input === "object" ? input : {{}},
    file_path: String(filePath),
    error: String(first(
      p.error?.message, p.error?.data?.message,
      info.error?.message, info.error?.data?.message
    )),
    cwd: String(first(p.directory, info.directory, directory)),
    timestamp: new Date().toISOString(),
  }}
}}

function structuredSkillSelection(...values) {{
  for (const value of values) {{
    if (!value || typeof value !== "object") continue
    const selected = first(
      value.selected_skill, value.selectedSkill,
      value.context?.selected_skill, value.context?.selectedSkill
    )
    if (selected && typeof selected === "object") {{
      const name = first(selected.name, selected.skill_name, selected.skillName)
      if (name) return {{
        skill_name: String(name),
        skill_path: String(first(
          selected.file_path, selected.filePath, selected.path
        )),
        activation_mode: "ui_selection",
        activation_source: "opencode.selected_skill",
      }}
    }}
    const collections = [
      value.parts, value.attachments,
      value.message?.parts, value.message?.content,
    ]
    for (const collection of collections) {{
      if (!Array.isArray(collection)) continue
      for (const part of collection.slice(0, 64)) {{
        if (!part || typeof part !== "object") continue
        const kind = String(first(part.type, part.kind, part.content_type)).toLowerCase()
        if (!["skill", "agent_skill", "skill_attachment", "skill_message"].includes(kind)) continue
        const name = first(part.name, part.skill, part.skill_name, part.id)
        if (!name) continue
        return {{
          skill_name: String(name),
          skill_path: String(first(part.file_path, part.filePath, part.path)),
          activation_mode: kind === "skill_message" ? "slash_command" : "ui_selection",
          activation_source: `opencode.structured_${{kind}}`,
        }}
      }}
    }}
  }}
  return {{}}
}}

function spawnFallback(args, body) {{
  if (!SETTINGS.fallback_executable) return
  try {{
    const child = spawn(
      SETTINGS.fallback_executable,
      ["hook", ...args.slice(0, 4)],
      {{ stdio: ["pipe", "ignore", "ignore"], detached: true }}
    )
    child.on("error", () => {{}})
    child.stdin.on("error", () => {{}})
    child.stdin.end(body)
    child.unref()
  }} catch (_) {{}}
}}

function deliver(hookEvent, payload) {{
  try {{
    if (!payload.session_id) return
    const body = JSON.stringify(payload)
    const args = [
      "--agent", "opencode", "--event", hookEvent,
      "--socket", SETTINGS.socket_path,
    ]
    if (!SETTINGS.native_sender) {{
      spawnFallback(args, body)
      return
    }}
    const child = spawn(
      SETTINGS.native_sender,
      args,
      {{ stdio: ["pipe", "ignore", "ignore"], detached: true }}
    )
    let fallbackStarted = false
    const fallbackOnce = () => {{
      if (fallbackStarted) return
      fallbackStarted = true
      spawnFallback(args, body)
    }}
    child.on("error", fallbackOnce)
    child.on("close", (code) => {{
      if (code !== 0) fallbackOnce()
    }})
    child.stdin.on("error", () => {{}})
    child.stdin.end(body)
    child.unref()
  }} catch (_) {{}}
}}

function emit(event, directory) {{
  try {{
    const hookEvent = EVENT_MAP[event?.type]
    if (!hookEvent) return
    deliver(hookEvent, minimalPayload(event, directory))
  }} catch (_) {{}}
}}

const SkillRuntimePlugin = async ({{ directory }}) => ({{
  event: async ({{ event }}) => {{
    emit(event, directory)
  }},
  "chat.message": async (input, output) => {{
    const selection = structuredSkillSelection(output, input)
    deliver("UserPromptSubmit", {{
      session_id: String(input?.sessionID || ""),
      turn_id: String(first(input?.messageID, input?.messageId, output?.message?.id)),
      ...selection,
      cwd: String(directory || ""),
      timestamp: new Date().toISOString(),
    }})
  }},
  "tool.execute.before": async (input, output) => {{
    deliver("PreToolUse", {{
      session_id: String(input?.sessionID || ""),
      tool_name: String(input?.tool || ""),
      tool_use_id: String(input?.callID || ""),
      tool_input: output?.args && typeof output.args === "object" ? output.args : {{}},
      cwd: String(directory || ""),
      timestamp: new Date().toISOString(),
    }})
  }},
  "tool.execute.after": async (input) => {{
    deliver("PostToolUse", {{
      session_id: String(input?.sessionID || ""),
      tool_name: String(input?.tool || ""),
      tool_use_id: String(input?.callID || ""),
      tool_input: input?.args && typeof input.args === "object" ? input.args : {{}},
      cwd: String(directory || ""),
      timestamp: new Date().toISOString(),
    }})
  }},
}})

export const SkillRuntimeIntelligence = SkillRuntimePlugin
"""


def inspect_opencode_integration(
    plugin_path: Optional[Path] = None,
    executable: str = "",
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (plugin_path or default_opencode_plugin_path()).expanduser()
    cli = _detect_cli_version("opencode")
    installed = False
    config_valid = True
    error = ""
    if path.exists():
        try:
            installed = OPENCODE_PLUGIN_MARKER in path.read_text(
                encoding="utf-8"
            )
            if not installed:
                config_valid = False
                error = "OpenCode plugin path exists but is not managed by Skill Runtime"
        except (OSError, UnicodeError) as exc:
            config_valid = False
            error = str(exc)
    return {
        "agent": "opencode",
        "detected": (Path.home() / ".config" / "opencode").is_dir()
        or bool(shutil.which("opencode")),
        "config_path": str(path),
        "config_exists": path.exists(),
        "config_valid": config_valid,
        "error": error,
        "executable": executable,
        "installed": installed,
        **cli,
        "installed_events": (
            sorted(
                {
                    "SessionStart",
                    "Stop",
                    "SessionError",
                    "UserPromptSubmit",
                    "PreToolUse",
                    "PostToolUse",
                }
            )
            if installed
            else []
        ),
        "planned_events": sorted(
            {
                "SessionStart",
                "Stop",
                "SessionError",
                "UserPromptSubmit",
                "PreToolUse",
                "PostToolUse",
            }
        ),
        "collection_mode": "official_hook",
        "selected_collection_mode": (
            "official_hook" if installed else "not_configured"
        ),
        "available_collection_modes": [
            "official_hook",
            "observability_import",
        ],
        "native_skill_telemetry": "not_detected",
        "fail_open": True,
        "async": True,
        "collector_endpoint": "http://127.0.0.1:4317/api/events",
        "fast_path": "detached_native_sender",
        "hook_socket": str(default_hook_socket()),
        "hook_socket_active": default_hook_socket().is_socket(),
        "native_sender": str(native_hook_sender_path(state_root)),
        "native_sender_available": native_hook_sender_path(state_root).is_file(),
        "offline_queue": str(default_event_queue()),
        "paths_read": [
            str(Path.home() / ".config" / "opencode" / "skills"),
            str(path),
        ],
        "changes_without_consent": [],
        "note": (
            "The managed plugin subscribes to public OpenCode events and starts "
            "delivery without awaiting it; it does not inspect or alter model requests."
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


def _atomic_write_text(path: Path, value: str, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
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
        group = {"hooks": [hook]}
        if matcher:
            group["matcher"] = matcher
        groups.append(group)
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


def enable_qoder_hooks(
    executable: str,
    config_path: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    path = (config_path or default_qoder_settings_path()).expanduser()
    return _enable_hooks(
        agent="qoder",
        integration_name="qoder-hooks",
        agent_label="Qoder",
        executable=executable,
        path=path,
        managed_events=MANAGED_QODER_EVENTS,
        state_root=state_root,
        asynchronous=False,
    )


def enable_opencode_plugin(
    executable: str,
    plugin_path: Optional[Path] = None,
    state_root: Optional[Path] = None,
) -> Dict[str, Any]:
    if not executable:
        raise IntegrationError("skill-runtime executable path is required")
    path = (plugin_path or default_opencode_plugin_path()).expanduser()
    if path.is_symlink():
        raise IntegrationError(f"refusing to replace symlinked plugin: {path}")
    source = _opencode_plugin_source(executable, state_root)
    if path.exists():
        try:
            existing = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            raise IntegrationError(f"unable to read OpenCode plugin: {exc}") from exc
        if OPENCODE_PLUGIN_MARKER not in existing:
            raise IntegrationError(
                f"refusing to replace unmanaged OpenCode plugin: {path}"
            )
        if existing == source:
            return {
                "changed": False,
                "installed_events": [
                    "SessionStart",
                    "Stop",
                    "SessionError",
                    "UserPromptSubmit",
                    "PreToolUse",
                    "PostToolUse",
                ],
                "config_path": str(path),
                "backup_path": None,
            }
    backup = _backup(path)
    original_mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    _atomic_write_text(path, source, original_mode)
    manifest = {
        "integration": "opencode-plugin-events",
        "managed_by": INTEGRATION_MARKER,
        "config_path": str(path),
        "executable": executable,
        "installed_events": [
            "SessionStart",
            "Stop",
            "SessionError",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
        ],
        "installed_at": datetime.now(timezone.utc).isoformat(),
        "backup_path": str(backup) if backup else None,
        "fail_open": True,
        "async": True,
    }
    manifest_path = (
        state_root or default_state_root()
    ) / "integrations" / "opencode.json"
    _atomic_write_json(manifest_path, manifest)
    return {
        "changed": True,
        "added_events": manifest["installed_events"],
        "installed_events": manifest["installed_events"],
        "config_path": str(path),
        "backup_path": str(backup) if backup else None,
        "manifest_path": str(manifest_path),
    }


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


def remove_qoder_hooks(
    config_path: Optional[Path] = None, state_root: Optional[Path] = None
) -> Dict[str, Any]:
    return _remove_hooks(
        agent="qoder",
        agent_label="Qoder",
        path=(config_path or default_qoder_settings_path()).expanduser(),
        state_root=state_root,
    )


def remove_opencode_plugin(
    plugin_path: Optional[Path] = None, state_root: Optional[Path] = None
) -> Dict[str, Any]:
    path = (plugin_path or default_opencode_plugin_path()).expanduser()
    if path.is_symlink():
        raise IntegrationError(f"refusing to remove symlinked plugin: {path}")
    if not path.exists():
        return {
            "changed": False,
            "removed_events": [],
            "config_path": str(path),
            "backup_path": None,
        }
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise IntegrationError(f"unable to read OpenCode plugin: {exc}") from exc
    if OPENCODE_PLUGIN_MARKER not in source:
        raise IntegrationError(
            f"refusing to remove unmanaged OpenCode plugin: {path}"
        )
    backup = _backup(path)
    path.unlink()
    manifest_path = (
        state_root or default_state_root()
    ) / "integrations" / "opencode.json"
    if manifest_path.exists():
        manifest_path.unlink()
    try:
        path.parent.rmdir()
        path.parent.parent.rmdir()
    except OSError:
        pass
    return {
        "changed": True,
        "removed_events": [
            "SessionStart",
            "Stop",
            "SessionError",
            "UserPromptSubmit",
            "PreToolUse",
            "PostToolUse",
        ],
        "config_path": str(path),
        "backup_path": str(backup) if backup else None,
    }
