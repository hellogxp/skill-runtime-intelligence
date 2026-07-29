"""Versioned, privacy-minimizing adapters for Agent lifecycle hooks."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .redaction import compact_text


CODEX_HOOK_ADAPTER_VERSION = "0.1.0"
CLAUDE_HOOK_ADAPTER_VERSION = "0.1.0"

HOOK_EVENT_TYPES = {
    "SessionStart": "session.started",
    "SessionEnd": "session.ended",
    "UserPromptSubmit": "turn.started",
    "UserPromptExpansion": "turn.started",
    "PreToolUse": "tool.started",
    "PostToolUse": "tool.completed",
    "PostToolUseFailure": "tool.failed",
    "PreCompact": "context.compaction_started",
    "PostCompact": "context.compaction_completed",
    "Stop": "turn.completed",
    "InstructionsLoaded": "instruction.loaded",
    "SubagentStart": "subagent.started",
    "SubagentStop": "subagent.completed",
    "FileChanged": "file.modified",
}

SUPPORTED_HOOK_AGENTS = {
    "codex": CODEX_HOOK_ADAPTER_VERSION,
    "claude-code": CLAUDE_HOOK_ADAPTER_VERSION,
}


def _get(value: Dict[str, Any], *paths: str) -> Any:
    for path in paths:
        current: Any = value
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current not in (None, ""):
            return current
    return None


def _stable_id(prefix: str, *parts: Any) -> str:
    value = "\0".join(str(part or "") for part in parts)
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _timestamp(payload: Dict[str, Any]) -> str:
    value = _get(payload, "timestamp", "occurred_at", "created_at")
    if value:
        return compact_text(value, 80)
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tool_name(payload: Dict[str, Any]) -> str:
    return compact_text(
        _get(
            payload,
            "tool_name",
            "toolName",
            "tool.name",
            "payload.tool_name",
            "payload.name",
        ),
        120,
    )


def _tool_input(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = _get(
        payload,
        "tool_input",
        "toolInput",
        "tool.input",
        "payload.tool_input",
        "payload.input",
    )
    return value if isinstance(value, dict) else {}


def _skill_name(payload: Dict[str, Any], tool_name: str) -> str:
    if tool_name.lower() != "skill":
        return compact_text(_get(payload, "skill_name", "skill.name"), 160)
    tool_input = _tool_input(payload)
    return compact_text(
        _get(
            tool_input,
            "skill",
            "skill_name",
            "name",
            "command",
        ),
        160,
    )


def _source_event_id(
    payload: Dict[str, Any], hook_event: str, session_id: str, occurred_at: str
) -> str:
    explicit = compact_text(
        _get(
            payload,
            "tool_use_id",
            "toolUseId",
            "call_id",
            "callId",
            "event_id",
            "eventId",
            "id",
        ),
        240,
    )
    if explicit:
        # Tool call IDs are only guaranteed within an Agent session. Scope the
        # identity so imports from concurrent/restarted Agents cannot collide.
        return _stable_id("hook_", session_id, explicit)
    return _stable_id("hook_", hook_event, session_id, occurred_at)


def _status(payload: Dict[str, Any], hook_event: str) -> Optional[str]:
    explicit = compact_text(_get(payload, "status", "payload.status"), 40).lower()
    if explicit in {
        "observed",
        "started",
        "completed",
        "failed",
        "denied",
        "interrupted",
        "unknown",
    }:
        return explicit
    if hook_event == "PostToolUseFailure":
        return "failed"
    if hook_event in {
        "PostToolUse",
        "PostCompact",
        "Stop",
        "SessionEnd",
        "SubagentStop",
    }:
        return "completed"
    if hook_event in {
        "PreToolUse",
        "PreCompact",
        "SessionStart",
        "SubagentStart",
    }:
        return "started"
    return None


def _file_path(payload: Dict[str, Any]) -> str:
    tool_input = _tool_input(payload)
    return compact_text(
        _get(
            payload,
            "file_path",
            "filePath",
            "payload.file_path",
            "tool_response.filePath",
            "tool_response.file_path",
        )
        or _get(tool_input, "file_path", "filePath", "path"),
        1000,
    )


def _file_event_type(payload: Dict[str, Any], hook_event: str) -> str:
    if hook_event == "FileChanged":
        change = compact_text(
            _get(payload, "event", "change", "change_type", "payload.event"), 40
        ).lower()
        if change in {"add", "added", "create", "created"}:
            return "file.created"
        if change in {"unlink", "delete", "deleted", "remove", "removed"}:
            return "file.deleted"
        return "file.modified"
    tool_name = _tool_name(payload).lower()
    if tool_name in {"write", "writefile", "createfile", "create_file"}:
        return "file.created"
    if tool_name in {
        "edit",
        "editfile",
        "applypatch",
        "apply_patch",
        "patch",
    }:
        return "file.modified"
    return ""


def _direct_slash_skill(payload: Dict[str, Any], hook_event: str) -> str:
    if hook_event != "UserPromptExpansion":
        return ""
    expansion_type = compact_text(
        _get(payload, "expansion_type", "expansionType"), 80
    ).lower()
    if expansion_type not in {"slash_command", "skill"}:
        return ""
    return compact_text(
        _get(payload, "command_name", "commandName", "skill_name"), 160
    ).lstrip("/")


def _looks_like_skill_instruction(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()
    return normalized.endswith("/skill.md") and (
        "/skills/" in normalized or "/.agents/" in normalized
    )


def build_agent_hook_envelopes(
    agent: str,
    adapter_version: str,
    hook_event: str,
    payload: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Map one official Agent hook invocation to minimal runtime envelopes.

    Unknown or uncorrelatable hooks are ignored rather than guessed. Full hook
    payloads, prompts, tool inputs, and tool outputs are intentionally omitted.
    """
    base_event_type = HOOK_EVENT_TYPES.get(hook_event)
    if not base_event_type or not isinstance(payload, dict):
        return []
    session_id = compact_text(
        _get(
            payload,
            "session_id",
            "sessionId",
            "session.id",
            "payload.session_id",
        ),
        256,
    )
    if not session_id:
        return []

    occurred_at = _timestamp(payload)
    turn_id = compact_text(
        _get(payload, "turn_id", "turnId", "turn.id", "payload.turn_id"), 256
    )
    tool_name = _tool_name(payload)
    skill_name = _skill_name(payload, tool_name) or _direct_slash_skill(
        payload, hook_event
    )
    instruction_path = _file_path(payload) if hook_event == "InstructionsLoaded" else ""
    if not skill_name and _looks_like_skill_instruction(instruction_path):
        skill_name = Path(instruction_path).parent.name
    source_event_id = _source_event_id(
        payload, hook_event, session_id, occurred_at
    )
    call_id = compact_text(
        _get(
            payload,
            "tool_use_id",
            "toolUseId",
            "call_id",
            "callId",
            "tool.id",
        ),
        256,
    )
    context = {
        "cwd": compact_text(_get(payload, "cwd", "workspace", "context.cwd"), 500),
        "model": compact_text(_get(payload, "model", "context.model"), 120),
        "agent_version": compact_text(
            _get(payload, "agent_version", "version", "context.agent_version"), 120
        ),
    }
    minimal_payload = {
        "hook_event": hook_event,
        "tool_name": tool_name,
        "call_id": call_id,
        "duration_ms": _get(payload, "duration_ms", "durationMs", "payload.duration_ms"),
        "exit_code": _get(payload, "exit_code", "exitCode", "payload.exit_code"),
        "error": compact_text(
            _get(payload, "error", "error_message", "payload.error"), 240
        ),
        "file_path": _file_path(payload),
        "agent_id": compact_text(_get(payload, "agent_id", "agentId"), 256),
        "agent_type": compact_text(_get(payload, "agent_type", "agentType"), 120),
        "load_reason": compact_text(
            _get(payload, "load_reason", "loadReason"), 120
        ),
    }
    minimal_payload = {
        key: value for key, value in minimal_payload.items() if value not in (None, "")
    }

    if hook_event == "FileChanged":
        event_type = _file_event_type(payload, hook_event)
    elif skill_name and hook_event in {"PreToolUse", "UserPromptExpansion"}:
        event_type = "skill.activated"
    elif skill_name and hook_event == "PostToolUse":
        event_type = "skill.activation_completed"
    elif skill_name and hook_event == "PostToolUseFailure":
        event_type = "skill.activation_failed"
    else:
        event_type = base_event_type

    event_id = _stable_id("evt_", f"{agent}-hook", source_event_id, event_type)
    parent_event_id = None
    if hook_event in {"PostToolUse", "PostToolUseFailure"} and call_id:
        parent_type = "skill.activated" if skill_name else "tool.started"
        parent_event_id = _stable_id(
            "evt_", f"{agent}-hook", source_event_id, parent_type
        )
    envelope: Dict[str, Any] = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "session_id": session_id,
        "turn_id": turn_id or None,
        "parent_event_id": parent_event_id,
        "source": {
            "adapter": agent,
            "adapter_version": adapter_version,
            "collection_mode": "official_hook",
            "source_event_id": source_event_id,
            "record_locator": f"{agent}-hook:{hook_event}:{source_event_id}",
        },
        "evidence": {
            "grade": "observed",
            "confidence": 1.0,
            "basis": f"{agent} {hook_event} official hook",
        },
        "context": context,
        "payload": minimal_payload,
        "summary": (
            f"Skill `{skill_name}` {event_type.split('.')[-1]}"
            if skill_name
            else f"{hook_event}: {tool_name or event_type}"
        ),
    }
    event_status = _status(payload, hook_event)
    if event_status:
        envelope["status"] = event_status
    if skill_name:
        envelope["skill"] = {"name": skill_name}
        envelope["activation_mode"] = (
            "slash_command"
            if hook_event == "UserPromptExpansion"
            else "explicit_tool"
        )

    envelopes = [envelope]
    file_event_type = _file_event_type(payload, hook_event)
    file_path = _file_path(payload)
    if file_event_type and file_path and hook_event == "PostToolUse":
        file_grade = "derived"
        file_event = {
            **envelope,
            "event_id": _stable_id(
                "evt_", f"{agent}-hook", source_event_id, file_event_type, file_path
            ),
            "event_type": file_event_type,
            "parent_event_id": event_id,
            "evidence": {
                "grade": file_grade,
                "confidence": 1.0,
                "basis": f"Exact path from successful {tool_name} official hook",
            },
            "payload": {
                "hook_event": hook_event,
                "tool_name": tool_name,
                "call_id": call_id,
                "file_path": file_path,
            },
            "summary": f"{file_event_type}: {file_path}",
            "status": "observed",
        }
        envelopes.append(file_event)
    return envelopes


def build_codex_hook_envelopes(
    hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return build_agent_hook_envelopes(
        "codex", CODEX_HOOK_ADAPTER_VERSION, hook_event, payload
    )


def build_claude_hook_envelopes(
    hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return build_agent_hook_envelopes(
        "claude-code", CLAUDE_HOOK_ADAPTER_VERSION, hook_event, payload
    )


def build_hook_envelopes(
    agent: str, hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    if agent == "codex":
        return build_codex_hook_envelopes(hook_event, payload)
    if agent == "claude-code":
        return build_claude_hook_envelopes(hook_event, payload)
    return []
