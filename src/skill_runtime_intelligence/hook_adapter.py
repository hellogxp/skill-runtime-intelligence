"""Versioned, privacy-minimizing adapters for Agent lifecycle hooks."""

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .redaction import compact_text


CODEX_HOOK_ADAPTER_VERSION = "0.3.0"
CLAUDE_HOOK_ADAPTER_VERSION = "0.3.0"
QODER_HOOK_ADAPTER_VERSION = "0.3.0"
OPENCODE_PLUGIN_ADAPTER_VERSION = "0.3.0"

QUOTED_SKILL_PATH = re.compile(
    r"""(?:
        "((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?/SKILL\.md)"
        |
        '((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?/SKILL\.md)'
        |
        ((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?/SKILL\.md)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
QUOTED_SKILL_RESOURCE_PATH = re.compile(
    r"""(?:
        "((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?skills/[^\s/"']+/
        (?:references|scripts|assets)/[^\s"'`|;&<>\r\n]+)"
        |
        '((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?skills/[^\s/"']+/
        (?:references|scripts|assets)/[^\s"'`|;&<>\r\n]+)'
        |
        ((?:~?/|\./|\.\./|[A-Za-z0-9._-]+/)
        [^\s"'`|;&<>\r\n]*?skills/[^\s/"']+/
        (?:references|scripts|assets)/[^\s"'`|;&<>\r\n]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
PATCH_FILE_PATH = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$", re.MULTILINE
)

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
    "SessionError": "turn.failed",
}

SUPPORTED_HOOK_AGENTS = {
    "codex": CODEX_HOOK_ADAPTER_VERSION,
    "claude-code": CLAUDE_HOOK_ADAPTER_VERSION,
    "qoder": QODER_HOOK_ADAPTER_VERSION,
    "opencode": OPENCODE_PLUGIN_ADAPTER_VERSION,
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


def _timestamp_metadata(payload: Dict[str, Any]) -> Dict[str, Any]:
    value = _get(payload, "timestamp", "occurred_at", "created_at")
    occurred_at = (
        compact_text(value, 80)
        if value
        else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    timestamp_origin = "source" if value else "adapter_fallback"
    clock_domain = compact_text(_get(payload, "clock_domain", "clockDomain"), 120)
    if not clock_domain:
        clock_domain = "source_reported" if value else "adapter_host"
    precision = "unknown"
    timestamp_text = str(occurred_at)
    if "." not in timestamp_text:
        precision = "seconds"
    else:
        fraction = timestamp_text.split(".", 1)[1].rstrip("Z")
        fraction = fraction.split("+", 1)[0].split("-", 1)[0]
        precision = {
            3: "milliseconds",
            6: "microseconds",
            9: "nanoseconds",
        }.get(len(fraction), "subsecond")
    return {
        "occurred_at": occurred_at,
        "timestamp_origin": timestamp_origin,
        "clock_domain": clock_domain,
        "clock_uncertainty_ms": _get(
            payload,
            "clock_uncertainty_ms",
            "clockUncertaintyMs",
        ),
        "timestamp_precision": precision,
    }


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


def _bounded_strings(value: Any, depth: int = 0) -> List[str]:
    """Return bounded string leaves for in-memory path extraction only."""
    if depth > 4:
        return []
    if isinstance(value, str):
        return [value[:131072]]
    if isinstance(value, dict):
        result: List[str] = []
        for index, item in enumerate(value.values()):
            if index >= 64:
                break
            result.extend(_bounded_strings(item, depth + 1))
        return result
    if isinstance(value, list):
        result = []
        for item in value[:64]:
            result.extend(_bounded_strings(item, depth + 1))
        return result
    return []


def _skill_instruction_paths(payload: Dict[str, Any]) -> List[str]:
    """Extract only exact Skill instruction paths and discard source strings.

    A Bash command or tool payload can contain credentials or source content,
    so the raw string is never copied into the normalized envelope. Only a
    normalized path ending in a standard Skill ``SKILL.md`` location survives.
    """
    cwd = compact_text(_get(payload, "cwd", "workspace", "context.cwd"), 1000)
    candidates = []
    structured = _file_path(payload)
    if structured:
        candidates.append(structured)
    for text in _bounded_strings(_tool_input(payload)):
        for match in QUOTED_SKILL_PATH.finditer(text):
            candidates.append(next(group for group in match.groups() if group))
    result = []
    seen = set()
    for candidate in candidates:
        cleaned = candidate.strip().rstrip(",:")
        try:
            expanded = Path(os.path.expanduser(cleaned))
            if not expanded.is_absolute() and cwd:
                expanded = Path(cwd) / expanded
            normalized = str(expanded.resolve(strict=False))
        except (OSError, RuntimeError, ValueError):
            continue
        if not _looks_like_skill_instruction(normalized):
            continue
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result[:16]


def _normalize_path(candidate: str, cwd: str) -> str:
    try:
        expanded = Path(os.path.expanduser(candidate.strip().rstrip(",:")))
        if not expanded.is_absolute() and cwd:
            expanded = Path(cwd) / expanded
        return str(expanded.resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return ""


def _skill_resource_identity(path: str) -> Optional[Dict[str, str]]:
    parts = Path(path).parts
    lower = [part.lower() for part in parts]
    for index, part in enumerate(lower):
        if part != "skills" or index + 3 >= len(parts):
            continue
        kind = lower[index + 2]
        if kind not in {"references", "scripts", "assets"}:
            continue
        return {
            "skill_name": parts[index + 1],
            "kind": kind,
            "path": path,
        }
    return None


def _skill_resource_paths(payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract exact standard Skill resource paths without retaining input."""
    cwd = compact_text(_get(payload, "cwd", "workspace", "context.cwd"), 1000)
    candidates = []
    structured = _file_path(payload)
    if structured:
        candidates.append(structured)
    for text in _bounded_strings(_tool_input(payload)):
        for match in QUOTED_SKILL_RESOURCE_PATH.finditer(text):
            candidates.append(next(group for group in match.groups() if group))
    result = []
    seen = set()
    for candidate in candidates:
        normalized = _normalize_path(candidate, cwd)
        identity = _skill_resource_identity(normalized)
        if not identity or normalized in seen:
            continue
        seen.add(normalized)
        result.append(identity)
    return result[:32]


def _changed_file_paths(payload: Dict[str, Any], tool_name: str) -> List[str]:
    """Extract only exact changed paths from structured inputs or patch headers."""
    cwd = compact_text(_get(payload, "cwd", "workspace", "context.cwd"), 1000)
    candidates = []
    structured = _file_path(payload)
    if structured:
        candidates.append(structured)
    if tool_name.lower() in {"applypatch", "apply_patch", "patch"}:
        for text in _bounded_strings(_tool_input(payload)):
            candidates.extend(PATCH_FILE_PATH.findall(text))
    result = []
    seen = set()
    for candidate in candidates:
        normalized = _normalize_path(candidate, cwd)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result[:64]


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
    if hook_event == "SessionError":
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


def _structured_skill_selection(payload: Dict[str, Any]) -> Dict[str, str]:
    """Extract an exact Skill selection from structured Agent metadata.

    Prompt text is deliberately excluded. Adapters may expose a selected Skill
    as a named object or a typed attachment/message part; only those explicit
    schemas are accepted.
    """
    name = compact_text(
        _get(
            payload,
            "selected_skill.name",
            "selected_skill.skill_name",
            "selectedSkill.name",
            "selectedSkill.skillName",
            "context.selected_skill.name",
            "context.selectedSkill.name",
        ),
        160,
    )
    path = compact_text(
        _get(
            payload,
            "selected_skill.file_path",
            "selected_skill.filePath",
            "selectedSkill.filePath",
            "context.selected_skill.file_path",
        ),
        1000,
    )
    source = "selected_skill"
    collections = (
        _get(payload, "attachments", "context.attachments"),
        _get(payload, "parts", "message.parts", "message.content"),
    )
    if not name:
        for collection in collections:
            if not isinstance(collection, list):
                continue
            for item in collection[:64]:
                if not isinstance(item, dict):
                    continue
                item_type = compact_text(
                    _get(item, "type", "kind", "content_type"), 80
                ).lower()
                if item_type not in {
                    "skill",
                    "agent_skill",
                    "skill_attachment",
                    "skill_message",
                }:
                    continue
                name = compact_text(
                    _get(item, "name", "skill", "skill_name", "id"), 160
                )
                path = compact_text(
                    _get(item, "file_path", "filePath", "path"), 1000
                )
                source = f"structured_{item_type}"
                if name:
                    break
            if name:
                break
    if not name:
        name = compact_text(_get(payload, "skill_name", "skill.name"), 160)
        if name:
            path = compact_text(
                _get(
                    payload,
                    "skill_path",
                    "skill.file_path",
                    "skill.filePath",
                    "skill.source_path",
                ),
                1000,
            )
            source = compact_text(
                _get(payload, "activation_source", "activationSource"), 120
            ) or "skill_name"
    if not name:
        explicit_mode = compact_text(
            _get(payload, "activation_mode", "activationMode"), 80
        ).lower()
        if explicit_mode in {
            "ui_selection",
            "slash_command",
            "automatic",
            "explicit_tool",
        }:
            name = compact_text(_get(payload, "skill_name", "skill.name"), 160)
            source = compact_text(
                _get(payload, "activation_source", "activationSource"), 120
            ) or "structured_activation"
    if not name:
        return {}
    return {"name": name, "path": path, "source": source}


def _qoder_transcript_skill_selection(payload: Dict[str, Any]) -> Dict[str, str]:
    """Read Qoder's bounded structured Skill-selection record, if present.

    Qoder serializes a UI Skill chip as ``session_meta/slash_command`` before
    the corresponding user record. Only the bounded JSONL tail is inspected;
    message content and tool payloads are never returned or persisted.
    """
    candidate = compact_text(
        _get(payload, "transcript_path", "transcriptPath"), 2000
    )
    session_id = compact_text(
        _get(payload, "session_id", "sessionId", "session.id"), 256
    )
    if not candidate or not session_id:
        return {}
    try:
        path = Path(candidate).expanduser().resolve(strict=True)
        parts = {part.casefold() for part in path.parts}
        if path.suffix.casefold() != ".jsonl" or ".qoder" not in parts:
            return {}
        if "transcript" not in parts or not path.is_file():
            return {}
        with path.open("rb") as source:
            source.seek(0, os.SEEK_END)
            size = source.tell()
            source.seek(max(0, size - 262144))
            tail = source.read(262144)
    except (OSError, RuntimeError, ValueError):
        return {}
    if tail and size > len(tail):
        tail = tail.split(b"\n", 1)[-1]
    records = []
    for line in tail.splitlines()[-256:]:
        try:
            record = json.loads(line)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if not isinstance(record, dict):
            continue
        if str(record.get("sessionId") or "") != session_id:
            continue
        records.append(record)
    if not records:
        return {}

    event_time = None
    event_time_value = _get(payload, "timestamp", "occurred_at", "created_at")
    if event_time_value:
        try:
            event_time = datetime.fromisoformat(
                str(event_time_value).replace("Z", "+00:00")
            )
        except ValueError:
            event_time = None

    anchor = None
    for index in range(len(records) - 1, -1, -1):
        record = records[index]
        if record.get("type") != "user":
            continue
        if event_time:
            try:
                record_time = datetime.fromisoformat(
                    str(record.get("timestamp") or "").replace("Z", "+00:00")
                )
            except ValueError:
                record_time = None
            if record_time and record_time > event_time + timedelta(seconds=5):
                continue
        content = _get(record, "message.content")
        if isinstance(content, list) and content and all(
            isinstance(item, dict) and item.get("type") == "tool_result"
            for item in content
        ):
            continue
        anchor = index
        break
    turn_id = ""
    if anchor is not None:
        turn_id = compact_text(records[anchor].get("uuid"), 256)
    search_end = anchor if anchor is not None else len(records)
    for index in range(search_end - 1, max(-1, search_end - 17), -1):
        record = records[index]
        if record.get("type") == "user":
            break
        data = record.get("data")
        if not isinstance(data, dict) or data.get("meta_type") != "slash_command":
            continue
        content = data.get("content")
        if not isinstance(content, dict) or content.get("type") != "skill":
            continue
        name = compact_text(content.get("name"), 160)
        if not name:
            continue
        return {
            "name": name,
            "path": compact_text(content.get("filePath"), 1000),
            "source": "qoder_session_meta.slash_command",
            "timestamp": compact_text(record.get("timestamp"), 80),
            "record_id": compact_text(record.get("uuid"), 256),
            "turn_id": turn_id,
        }
    return {"turn_id": turn_id} if turn_id else {}


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

    timestamp_metadata = _timestamp_metadata(payload)
    occurred_at = timestamp_metadata["occurred_at"]
    turn_id = compact_text(
        _get(payload, "turn_id", "turnId", "turn.id", "payload.turn_id"), 256
    )
    tool_name = _tool_name(payload)
    named_skill = _skill_name(payload, tool_name)
    slash_skill = _direct_slash_skill(payload, hook_event)
    selection = (
        _structured_skill_selection(payload)
        if hook_event in {"UserPromptSubmit", "UserPromptExpansion"}
        else {}
    )
    skill_name = named_skill or slash_skill or selection.get("name", "")
    explicit_skill_tool = tool_name.casefold() == "skill" and bool(named_skill)
    activation_start = bool(
        skill_name
        and (
            (hook_event == "PreToolUse" and explicit_skill_tool)
            or hook_event == "UserPromptExpansion"
            or (hook_event == "UserPromptSubmit" and selection)
        )
    )
    activation_mode = "unknown"
    if explicit_skill_tool:
        activation_mode = "explicit_tool"
    elif slash_skill or hook_event == "UserPromptExpansion":
        activation_mode = "slash_command"
    elif selection:
        activation_mode = compact_text(
            _get(payload, "activation_mode", "activationMode"), 80
        ).lower() or "ui_selection"
    instruction_paths = _skill_instruction_paths(payload)
    skill_resources = _skill_resource_paths(payload)
    instruction_path = _file_path(payload) if hook_event == "InstructionsLoaded" else ""
    if not skill_name and _looks_like_skill_instruction(instruction_path):
        skill_name = Path(instruction_path).parent.name
    if hook_event == "InstructionsLoaded" and skill_name:
        activation_mode = "instruction_evidence"
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
        "activation_source": (
            selection.get("source", "")
            or compact_text(
                _get(payload, "activation_source", "activationSource"), 120
            )
        ),
    }
    minimal_payload = {
        key: value for key, value in minimal_payload.items() if value not in (None, "")
    }

    if hook_event == "FileChanged":
        event_type = _file_event_type(payload, hook_event)
    elif activation_start and hook_event != "UserPromptSubmit":
        event_type = "skill.activated"
    elif explicit_skill_tool and hook_event == "PostToolUse":
        event_type = "skill.activation_completed"
    elif explicit_skill_tool and hook_event == "PostToolUseFailure":
        event_type = "skill.activation_failed"
    else:
        event_type = base_event_type

    event_id = _stable_id("evt_", f"{agent}-hook", source_event_id, event_type)
    parent_event_id = None
    if hook_event in {"PostToolUse", "PostToolUseFailure"} and call_id:
        parent_type = "skill.activated" if explicit_skill_tool else "tool.started"
        parent_event_id = _stable_id(
            "evt_", f"{agent}-hook", source_event_id, parent_type
        )
    envelope: Dict[str, Any] = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "timestamp_origin": timestamp_metadata["timestamp_origin"],
        "clock_domain": timestamp_metadata["clock_domain"],
        "clock_uncertainty_ms": timestamp_metadata["clock_uncertainty_ms"],
        "timestamp_precision": timestamp_metadata["timestamp_precision"],
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
    prompt_with_selection = hook_event == "UserPromptSubmit" and bool(selection)
    if skill_name and not prompt_with_selection:
        skill_record = {"name": skill_name}
        skill_path = selection.get("path", "") or instruction_path
        if skill_path and _looks_like_skill_instruction(skill_path):
            skill_record["source_path"] = skill_path
        envelope["skill"] = skill_record
        envelope["activation_mode"] = activation_mode

    envelopes = [envelope]
    if prompt_with_selection:
        activation_source_id = _stable_id(
            "hook_", source_event_id, "skill.activated", skill_name
        )
        activation_payload = dict(minimal_payload)
        activation_payload["activation_source"] = selection.get(
            "source", "structured_selection"
        )
        activation = {
            **envelope,
            "event_id": _stable_id(
                "evt_", f"{agent}-hook", activation_source_id, "skill.activated"
            ),
            "event_type": "skill.activated",
            "parent_event_id": event_id,
            "source": {
                **envelope["source"],
                "source_event_id": activation_source_id,
                "record_locator": (
                    f"{agent}-hook:{hook_event}:{activation_source_id}"
                ),
            },
            "evidence": {
                "grade": "observed",
                "confidence": 1.0,
                "basis": (
                    f"{agent} {hook_event} exposed an exact structured "
                    "Skill selection"
                ),
            },
            "payload": activation_payload,
            "summary": f"Skill `{skill_name}` selected",
            "status": "started",
            "skill": {"name": skill_name},
            "activation_mode": activation_mode,
        }
        skill_path = selection.get("path", "")
        if skill_path and _looks_like_skill_instruction(skill_path):
            activation["skill"]["source_path"] = skill_path
        envelopes.append(activation)
    if hook_event == "PostToolUse":
        for path in instruction_paths:
            instruction_source_id = _stable_id(
                "hook_", source_event_id, "instruction.loaded", path
            )
            envelopes.append(
                {
                    **envelope,
                    "event_id": _stable_id(
                        "evt_",
                        f"{agent}-hook",
                        instruction_source_id,
                        "instruction.loaded",
                    ),
                    "event_type": "instruction.loaded",
                    "parent_event_id": event_id,
                    "source": {
                        **envelope["source"],
                        "source_event_id": instruction_source_id,
                        "record_locator": (
                            f"{agent}-hook:{hook_event}:{instruction_source_id}"
                        ),
                    },
                    "evidence": {
                        "grade": "derived",
                        "confidence": 1.0,
                        "basis": (
                            "Exact SKILL.md path extracted from a successful "
                            f"{tool_name or 'tool'} official hook; raw input omitted"
                        ),
                    },
                    "skill": {
                        "name": Path(path).parent.name,
                        "source_path": path,
                    },
                    "activation_mode": "instruction_access",
                    "payload": {
                        "hook_event": hook_event,
                        "tool_name": tool_name,
                        "call_id": call_id,
                        "file_path": path,
                        "resource_kind": "skill_body",
                    },
                    "summary": (
                        f"Skill `{Path(path).parent.name}` instruction accessed"
                    ),
                    "status": "completed",
                }
            )
        for resource in skill_resources:
            resource_event_type = (
                "resource.executed"
                if resource["kind"] == "scripts"
                and tool_name.lower() in {"bash", "shell", "exec", "execute"}
                else "resource.read"
            )
            resource_source_id = _stable_id(
                "hook_", source_event_id, resource_event_type, resource["path"]
            )
            envelopes.append(
                {
                    **envelope,
                    "event_id": _stable_id(
                        "evt_",
                        f"{agent}-hook",
                        resource_source_id,
                        resource_event_type,
                    ),
                    "event_type": resource_event_type,
                    "parent_event_id": event_id,
                    "source": {
                        **envelope["source"],
                        "source_event_id": resource_source_id,
                        "record_locator": (
                            f"{agent}-hook:{hook_event}:{resource_source_id}"
                        ),
                    },
                    "evidence": {
                        "grade": "derived",
                        "confidence": 1.0,
                        "basis": (
                            "Exact standard Skill resource path extracted from "
                            f"a successful {tool_name or 'tool'} official hook; "
                            "raw input omitted"
                        ),
                    },
                    "skill": {
                        "name": resource["skill_name"],
                    },
                    "activation_mode": "resource_access",
                    "payload": {
                        "hook_event": hook_event,
                        "tool_name": tool_name,
                        "call_id": call_id,
                        "file_path": resource["path"],
                        "resource_kind": resource["kind"],
                    },
                    "summary": (
                        f"Skill `{resource['skill_name']}` "
                        f"{resource_event_type.split('.')[-1]} "
                        f"{resource['kind']} resource"
                    ),
                    "status": "completed",
                }
            )
    file_event_type = _file_event_type(payload, hook_event)
    changed_paths = _changed_file_paths(payload, tool_name)
    if file_event_type and changed_paths and hook_event == "PostToolUse":
        for file_path in changed_paths:
            file_source_id = _stable_id(
                "hook_", source_event_id, file_event_type, file_path
            )
            file_event = {
                **envelope,
                "event_id": _stable_id(
                    "evt_",
                    f"{agent}-hook",
                    file_source_id,
                    file_event_type,
                ),
                "event_type": file_event_type,
                "parent_event_id": event_id,
                "source": {
                    **envelope["source"],
                    "source_event_id": file_source_id,
                    "record_locator": (
                        f"{agent}-hook:{hook_event}:{file_source_id}"
                    ),
                },
                "evidence": {
                    "grade": "derived",
                    "confidence": 1.0,
                    "basis": (
                        f"Exact changed path from successful {tool_name} "
                        "official hook; file content omitted"
                    ),
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


def build_qoder_hook_envelopes(
    hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    transcript_context = _qoder_transcript_skill_selection(payload)
    effective_payload = payload
    if transcript_context.get("turn_id") and not _get(
        payload, "turn_id", "turnId", "turn.id"
    ):
        effective_payload = dict(payload)
        effective_payload["turn_id"] = transcript_context["turn_id"]
    envelopes = build_agent_hook_envelopes(
        "qoder", QODER_HOOK_ADAPTER_VERSION, hook_event, effective_payload
    )
    if hook_event not in {"UserPromptSubmit", "PreToolUse"} or any(
        item.get("event_type") == "skill.activated" for item in envelopes
    ):
        return envelopes
    selection = transcript_context
    if not selection.get("name"):
        return envelopes
    synthetic = {
        "session_id": _get(payload, "session_id", "sessionId", "session.id"),
        "turn_id": _get(
            effective_payload, "turn_id", "turnId", "turn.id"
        ),
        "timestamp": selection.get("timestamp") or _get(payload, "timestamp"),
        "event_id": selection.get("record_id"),
        "expansion_type": "slash_command",
        "command_name": selection["name"],
        "skill_name": selection["name"],
        "skill_path": selection.get("path", ""),
        "activation_source": selection["source"],
        "cwd": _get(effective_payload, "cwd", "workspace", "context.cwd"),
        "model": _get(effective_payload, "model", "context.model"),
        "agent_version": _get(
            effective_payload,
            "agent_version",
            "version",
            "context.agent_version",
        ),
    }
    activation = build_agent_hook_envelopes(
        "qoder", QODER_HOOK_ADAPTER_VERSION, "UserPromptExpansion", synthetic
    )
    if activation:
        activation[0]["source"]["record_locator"] = (
            "qoder-transcript:session_meta:"
            + (selection.get("record_id") or activation[0]["source"]["source_event_id"])
        )
        activation[0]["evidence"]["basis"] = (
            "Exact Qoder session_meta/slash_command Skill record; "
            "conversation content omitted"
        )
        activation[0]["payload"]["activation_source"] = selection["source"]
        activation[0]["summary"] = f"Skill `{selection['name']}` selected"
        return activation + envelopes
    return envelopes


def build_opencode_hook_envelopes(
    hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    return build_agent_hook_envelopes(
        "opencode", OPENCODE_PLUGIN_ADAPTER_VERSION, hook_event, payload
    )


def build_hook_envelopes(
    agent: str, hook_event: str, payload: Dict[str, Any]
) -> List[Dict[str, Any]]:
    if agent == "codex":
        return build_codex_hook_envelopes(hook_event, payload)
    if agent == "claude-code":
        return build_claude_hook_envelopes(hook_event, payload)
    if agent == "qoder":
        return build_qoder_hook_envelopes(hook_event, payload)
    if agent == "opencode":
        return build_opencode_hook_envelopes(hook_event, payload)
    return []
