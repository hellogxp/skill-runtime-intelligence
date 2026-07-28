"""Codex JSONL session adapter.

The adapter intentionally handles a narrow set of stable-looking records and
surfaces all other signals as unsupported rather than inventing facts.
"""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..discovery import SkillDefinition
from ..redaction import compact_text, redact, redacted_json


ADAPTER_NAME = "codex"
ADAPTER_VERSION = "0.1.0"
SOURCE_FORMAT_VERSION = "codex-jsonl-observed-2026-07"


def _stable_id(prefix: str, *parts: Any) -> str:
    digest = hashlib.sha256(
        "\0".join("" if part is None else str(part) for part in parts).encode("utf-8")
    ).hexdigest()
    return f"{prefix}_{digest[:24]}"


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _duration_ms(start: Optional[str], end: Optional[str]) -> Optional[int]:
    start_time = _parse_time(start)
    end_time = _parse_time(end)
    if not start_time or not end_time:
        return None
    return max(0, int((end_time - start_time).total_seconds() * 1000))


def _input_text(payload: Dict[str, Any]) -> str:
    value = payload.get("input", payload.get("arguments", ""))
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _tool_name(payload: Dict[str, Any]) -> str:
    return str(payload.get("name") or payload.get("tool_name") or "unknown")


def _path_in_text(path: str, text: str) -> bool:
    variants = {path}
    if path.startswith("/private/"):
        variants.add(path[len("/private"):])
    elif path.startswith("/var/"):
        variants.add("/private" + path)
    return any(candidate in text for candidate in variants)


class CodexAdapter:
    name = ADAPTER_NAME
    version = ADAPTER_VERSION

    def __init__(self, sessions_root: Path):
        self.sessions_root = sessions_root.expanduser()

    def session_files(self) -> Iterable[Path]:
        if not self.sessions_root.is_dir():
            return []
        return sorted(self.sessions_root.rglob("*.jsonl"))

    def parse(
        self, source_path: Path, skills: List[SkillDefinition]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
        records = []
        malformed = False
        with source_path.open("r", encoding="utf-8", errors="replace") as handle:
            for line_number, line in enumerate(handle, 1):
                try:
                    records.append((line_number, line, json.loads(line)))
                except json.JSONDecodeError:
                    malformed = True

        meta = next(
            (record for _, _, record in records if record.get("type") == "session_meta"),
            {},
        )
        meta_payload = meta.get("payload", {})
        session_id = str(
            meta_payload.get("session_id")
            or meta_payload.get("id")
            or _stable_id("session", str(source_path.resolve()))
        )
        source_resolved = str(source_path.resolve())
        raw_records = []
        events = []
        skill_runs_by_id: Dict[str, Dict[str, Any]] = {}
        tool_calls: Dict[str, Dict[str, Any]] = {}
        active_turn = None
        open_turns = set()
        started_at = meta.get("timestamp") or meta_payload.get("timestamp")
        last_timestamp = started_at
        title = ""
        model = ""
        completed_duration = 0
        saw_completion = False

        for line_number, line, record in records:
            outer_type = str(record.get("type") or "unknown")
            payload = record.get("payload")
            payload = payload if isinstance(payload, dict) else {}
            payload_type = str(payload.get("type") or "")
            timestamp = record.get("timestamp") or payload.get("timestamp")
            if timestamp:
                last_timestamp = timestamp
                if not started_at:
                    started_at = timestamp

            envelope = {
                "type": outer_type,
                "payload_type": payload_type,
                "payload_keys": sorted(payload.keys()),
            }
            for safe_key in ("name", "call_id", "id", "status"):
                if safe_key in payload:
                    envelope[safe_key] = payload[safe_key]
            raw_records.append(
                {
                    "raw_id": _stable_id("raw", session_id, line_number),
                    "session_id": session_id,
                    "adapter": self.name,
                    "source_path": source_resolved,
                    "line_number": line_number,
                    "record_hash": hashlib.sha256(line.encode("utf-8")).hexdigest(),
                    "occurred_at": timestamp,
                    "record_type": f"{outer_type}.{payload_type}".rstrip("."),
                    "redacted_envelope_json": redacted_json(envelope),
                }
            )

            if outer_type == "turn_context":
                active_turn = str(payload.get("turn_id") or active_turn or "")
                model = str(payload.get("model") or model)
                continue

            if outer_type == "event_msg" and payload_type == "task_started":
                active_turn = str(payload.get("turn_id") or _stable_id("turn", session_id, line_number))
                open_turns.add(active_turn)
                events.append(
                    self._event(
                        session_id, line_number, timestamp, "turn.started", "request",
                        "observed", "Codex task_started event", "Turn started",
                        source_resolved, active_turn, payload={"turn_id": active_turn},
                    )
                )
                continue

            if outer_type == "event_msg" and payload_type == "user_message":
                message = payload.get("message", "")
                if not title:
                    title = compact_text(message, 100) or "Untitled Codex session"
                events.append(
                    self._event(
                        session_id, line_number, timestamp, "request.received", "request",
                        "observed", "Codex user_message event",
                        compact_text(message, 180) or "User request received",
                        source_resolved, active_turn,
                    )
                )
                continue

            if outer_type == "event_msg" and payload_type == "task_complete":
                turn_id = str(payload.get("turn_id") or active_turn or "")
                open_turns.discard(turn_id)
                duration = payload.get("duration_ms")
                if isinstance(duration, (int, float)):
                    completed_duration += int(duration)
                saw_completion = True
                events.append(
                    self._event(
                        session_id, line_number, timestamp, "turn.completed", "outcome",
                        "observed", "Codex task_complete event", "Turn completed",
                        source_resolved, turn_id, status="completed",
                        payload={"duration_ms": duration},
                    )
                )
                continue

            if outer_type == "event_msg" and payload_type == "agent_message":
                events.append(
                    self._event(
                        session_id, line_number, timestamp, "outcome.reported", "outcome",
                        "observed", "Codex agent_message event",
                        compact_text(payload.get("message"), 180) or "Agent reported an outcome",
                        source_resolved, active_turn, status="reported",
                    )
                )
                continue

            if outer_type != "response_item":
                continue

            if payload_type in ("function_call", "custom_tool_call", "tool_search_call"):
                name = _tool_name(payload)
                call_id = str(payload.get("call_id") or payload.get("id") or _stable_id("call", line_number))
                event = self._event(
                    session_id, line_number, timestamp, "tool.started", "execution",
                    "observed", f"Codex {payload_type} record", f"Tool `{name}` started",
                    source_resolved, active_turn,
                    payload={"tool_name": name, "call_id": call_id},
                )
                events.append(event)
                tool_calls[call_id] = {"event_id": event["event_id"], "name": name}
                input_text = _input_text(payload)
                self._detect_skill_evidence(
                    session_id, line_number, timestamp, source_resolved, active_turn,
                    name, input_text, skills, event["event_id"], events, skill_runs_by_id,
                )
                continue

            if payload_type in (
                "function_call_output", "custom_tool_call_output", "tool_search_output"
            ):
                call_id = str(payload.get("call_id") or payload.get("id") or "")
                parent = tool_calls.get(call_id, {})
                name = parent.get("name", "unknown")
                events.append(
                    self._event(
                        session_id, line_number, timestamp, "tool.completed", "execution",
                        "observed", f"Codex {payload_type} record",
                        f"Tool `{name}` completed", source_resolved, active_turn,
                        status="completed", parent_event_id=parent.get("event_id"),
                        payload={"tool_name": name, "call_id": call_id},
                    )
                )

        ended_at = last_timestamp if saw_completion and not open_turns else None
        status = "completed" if saw_completion and not open_turns else "incomplete"
        completeness = "incomplete" if malformed or open_turns else "complete"
        for run in skill_runs_by_id.values():
            run["status"] = status
            run["ended_at"] = ended_at
        session = {
            "session_id": session_id,
            "adapter": self.name,
            "adapter_version": self.version,
            "source_path": source_resolved,
            "source_format_version": SOURCE_FORMAT_VERSION,
            "title": title or source_path.stem,
            "cwd": str(meta_payload.get("cwd") or ""),
            "model": model,
            "agent_version": str(meta_payload.get("cli_version") or ""),
            "started_at": started_at,
            "ended_at": ended_at,
            "duration_ms": completed_duration or _duration_ms(started_at, ended_at),
            "status": status,
            "completeness": completeness,
            "event_count": len(events),
        }
        return session, raw_records, events, list(skill_runs_by_id.values())

    def _detect_skill_evidence(
        self,
        session_id: str,
        line_number: int,
        timestamp: Optional[str],
        source_path: str,
        turn_id: Optional[str],
        tool_name: str,
        input_text: str,
        skills: List[SkillDefinition],
        parent_event_id: str,
        events: List[Dict[str, Any]],
        skill_runs: Dict[str, Dict[str, Any]],
    ) -> None:
        lower_tool = tool_name.lower()
        for skill in skills:
            skill_file = skill.source_path
            skill_dir = str(Path(skill_file).parent)
            explicit = lower_tool == "skill" and skill.name.lower() in input_text.lower()
            instruction_loaded = _path_in_text(skill_file, input_text)
            resource_accessed = _path_in_text(skill_dir, input_text) and not instruction_loaded
            if not (explicit or instruction_loaded or resource_accessed):
                continue

            if explicit:
                event_type = "skill.activated"
                stage = "activation"
                grade = "observed"
                activation_mode = "explicit_tool"
                basis = "Codex tool input explicitly names the Skill"
                summary = f"Skill `{skill.name}` explicitly activated"
            elif instruction_loaded:
                event_type = "instruction.loaded"
                stage = "instructions"
                grade = "observed"
                activation_mode = "unknown"
                basis = "Observed tool input contains the exact SKILL.md path"
                summary = f"`{skill.name}` instructions loaded"
            else:
                event_type = "resource.read"
                stage = "resources"
                grade = "observed"
                activation_mode = "unknown"
                basis = "Observed tool input contains the exact Skill directory path"
                summary = f"`{skill.name}` resource accessed"

            event = self._event(
                session_id, line_number, timestamp, event_type, stage, grade, basis,
                summary, source_path, turn_id, skill_id=skill.skill_id,
                parent_event_id=parent_event_id,
                payload={"skill_name": skill.name, "tool_name": tool_name},
                suffix=skill.skill_id,
            )
            events.append(event)
            run_id = _stable_id("skillrun", session_id, skill.skill_id)
            if run_id not in skill_runs:
                skill_runs[run_id] = {
                    "skill_run_id": run_id,
                    "session_id": session_id,
                    "skill_id": skill.skill_id,
                    "activation_mode": activation_mode,
                    "evidence_grade": grade if explicit else "derived",
                    "status": "incomplete",
                    "started_at": timestamp,
                    "ended_at": None,
                    "basis": basis if explicit else (
                        "Skill scope derived from an observed access to its exact filesystem path"
                    ),
                }

    @staticmethod
    def _event(
        session_id: str,
        line_number: int,
        timestamp: Optional[str],
        event_type: str,
        stage: str,
        grade: str,
        basis: str,
        summary: str,
        source_path: str,
        turn_id: Optional[str],
        status: str = "observed",
        confidence: float = 1.0,
        skill_id: Optional[str] = None,
        parent_event_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        suffix: str = "",
    ) -> Dict[str, Any]:
        return {
            "event_id": _stable_id("evt", session_id, line_number, event_type, suffix),
            "session_id": session_id,
            "turn_id": turn_id,
            "skill_id": skill_id,
            "parent_event_id": parent_event_id,
            "occurred_at": timestamp,
            "event_type": event_type,
            "stage": stage,
            "status": status,
            "evidence_grade": grade,
            "confidence": confidence,
            "basis": basis,
            "summary": compact_text(summary, 220),
            "source_locator": f"{source_path}:{line_number}",
            "payload": redact(payload or {}),
        }
