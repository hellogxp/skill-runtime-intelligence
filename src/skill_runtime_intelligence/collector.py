"""Validation and normalization for the local runtime event collector."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List

from .redaction import compact_text, redact, redacted_json


EVENT_STAGES = {
    "session.started": "request",
    "session.ended": "outcome",
    "session.compacted": "request",
    "context.compaction_started": "request",
    "context.compaction_completed": "request",
    "turn.started": "request",
    "turn.completed": "outcome",
    "turn.failed": "outcome",
    "skill.discovered": "discovery",
    "skill.discovery_failed": "discovery",
    "skill.activated": "activation",
    "skill.activation_completed": "activation",
    "skill.activation_failed": "activation",
    "skill.deactivated": "activation",
    "instruction.loaded": "instructions",
    "resource.read": "resources",
    "resource.executed": "resources",
    "resource.missing": "resources",
    "resource.load_failed": "resources",
    "tool.requested": "execution",
    "tool.started": "execution",
    "tool.completed": "execution",
    "tool.failed": "execution",
    "tool.denied": "execution",
    "subagent.started": "execution",
    "subagent.completed": "execution",
    "subagent.failed": "execution",
    "file.read": "resources",
    "file.created": "artifacts",
    "file.modified": "artifacts",
    "file.deleted": "artifacts",
    "artifact.produced": "artifacts",
    "artifact.inspected": "artifacts",
    "outcome.reported": "outcome",
    "outcome.verified": "outcome",
    "outcome.unknown": "outcome",
}

VALID_EVIDENCE_GRADES = {"observed", "derived", "inferred", "experimental"}
VALID_COLLECTION_MODES = {
    "native_telemetry",
    "official_hook",
    "lightweight_hook",
    "sdk",
}
TERMINAL_SESSION_EVENTS = {"session.ended"}
TERMINAL_SKILL_EVENTS = {
    "skill.activation_completed",
    "skill.activation_failed",
    "skill.deactivated",
    "outcome.reported",
    "outcome.verified",
    "turn.completed",
    "turn.failed",
}


class CollectorValidationError(ValueError):
    """Raised when a submitted runtime event violates the collector contract."""


def _identifier(value: Any, field: str, required: bool = False) -> str:
    result = str(value or "").strip()
    if required and not result:
        raise CollectorValidationError(f"{field} is required")
    if len(result) > 256 or "\n" in result or "\r" in result:
        raise CollectorValidationError(f"{field} must be a single line <= 256 chars")
    return result


def _timestamp(value: Any) -> str:
    if value is None or value == "":
        return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = _identifier(value, "occurred_at", required=True)
    try:
        datetime.fromisoformat(result.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CollectorValidationError("occurred_at must be an ISO-8601 timestamp") from exc
    return result


def _event_status(event_type: str, explicit_status: Any) -> str:
    if explicit_status:
        status = _identifier(explicit_status, "status", required=True).lower()
        if status not in {
            "observed",
            "started",
            "completed",
            "failed",
            "denied",
            "interrupted",
            "unknown",
        }:
            raise CollectorValidationError(f"unsupported status: {status}")
        return status
    if event_type.endswith((".failed", ".missing")):
        return "failed"
    if event_type.endswith((".completed", ".verified", ".produced", ".ended")):
        return "completed"
    if event_type.endswith(".denied"):
        return "denied"
    if event_type.endswith((".started", ".requested", ".activated")):
        return "started"
    return "observed"


def _skill_status(event_type: str, event_status: str) -> str:
    if event_type in {"skill.activation_failed"}:
        return "failed"
    if event_type in TERMINAL_SKILL_EVENTS:
        return "failed" if event_status == "failed" else "completed"
    return "incomplete"


def _stable_id(prefix: str, *parts: Any, length: int = 24) -> str:
    value = "\0".join(str(part or "") for part in parts)
    return prefix + hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def normalize_collector_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """Convert one collector envelope into storage-ready, redacted records."""
    if not isinstance(envelope, dict):
        raise CollectorValidationError("each event must be a JSON object")

    source = envelope.get("source")
    if not isinstance(source, dict):
        raise CollectorValidationError("source must be an object")
    adapter = _identifier(source.get("adapter"), "source.adapter", required=True)
    adapter_version = _identifier(
        source.get("adapter_version") or "unknown",
        "source.adapter_version",
        required=True,
    )
    collection_mode = _identifier(
        source.get("collection_mode") or "sdk",
        "source.collection_mode",
        required=True,
    )
    if collection_mode not in VALID_COLLECTION_MODES:
        raise CollectorValidationError(
            f"unsupported source.collection_mode: {collection_mode}"
        )

    source_session_id = _identifier(
        envelope.get("session_id"), "session_id", required=True
    )
    internal_session_id = _stable_id(
        "live_session_", adapter, collection_mode, source_session_id
    )
    turn_id = _identifier(envelope.get("turn_id"), "turn_id") or None
    event_type = _identifier(
        envelope.get("event_type"), "event_type", required=True
    )
    if event_type not in EVENT_STAGES:
        raise CollectorValidationError(f"unsupported event_type: {event_type}")
    occurred_at = _timestamp(envelope.get("occurred_at"))
    status = _event_status(event_type, envelope.get("status"))

    evidence = envelope.get("evidence") or {}
    if not isinstance(evidence, dict):
        raise CollectorValidationError("evidence must be an object")
    evidence_grade = _identifier(
        evidence.get("grade") or "observed", "evidence.grade", required=True
    ).lower()
    if evidence_grade not in VALID_EVIDENCE_GRADES:
        raise CollectorValidationError(
            f"unsupported evidence.grade: {evidence_grade}"
        )
    try:
        confidence = float(evidence.get("confidence", 1.0))
    except (TypeError, ValueError) as exc:
        raise CollectorValidationError("evidence.confidence must be numeric") from exc
    if not 0.0 <= confidence <= 1.0:
        raise CollectorValidationError("evidence.confidence must be between 0 and 1")
    basis = compact_text(
        evidence.get("basis")
        or f"{collection_mode.replace('_', ' ')} event from {adapter}",
        300,
    )

    redacted_envelope = redact(envelope)
    source_event_id = _identifier(source.get("source_event_id"), "source.source_event_id")
    supplied_event_id = _identifier(envelope.get("event_id"), "event_id")
    if supplied_event_id:
        event_id = supplied_event_id
    elif source_event_id:
        event_id = _stable_id("evt_", adapter, source_event_id)
    else:
        event_id = _stable_id(
            "evt_",
            adapter,
            source_session_id,
            event_type,
            occurred_at,
            json.dumps(redacted_envelope, ensure_ascii=False, sort_keys=True),
        )

    skill_value = envelope.get("skill")
    skill: Dict[str, Any] = {}
    if isinstance(skill_value, str):
        skill = {"name": skill_value}
    elif isinstance(skill_value, dict):
        skill = dict(skill_value)
    elif skill_value is not None:
        raise CollectorValidationError("skill must be a name or object")
    skill_name = _identifier(
        skill.get("name") or envelope.get("skill_name"), "skill.name"
    )
    skill_record = None
    skill_id = None
    skill_run = None
    skill_run_id = _identifier(envelope.get("skill_run_id"), "skill_run_id") or None
    if skill_name:
        skill_source_path = str(
            skill.get("source_path") or f"collector://{adapter}/skills/{skill_name}"
        )
        skill_id = _stable_id("skill_", skill_source_path, length=20)
        skill_digest = _identifier(skill.get("digest"), "skill.digest") or hashlib.sha256(
            skill_source_path.encode("utf-8")
        ).hexdigest()
        skill_record = {
            "skill_id": skill_id,
            "name": skill_name,
            "description": compact_text(skill.get("description"), 500),
            "source_kind": _identifier(skill.get("source_kind"), "skill.source_kind")
            or "runtime",
            "source_path": skill_source_path,
            "digest": skill_digest,
            "valid": True,
            "validation_message": "",
        }
        if not skill_run_id:
            run_token = envelope.get("run_token") or turn_id or "session"
            skill_run_id = _stable_id(
                "skillrun_",
                adapter,
                collection_mode,
                source_session_id,
                run_token,
                skill_id,
            )
        run_status = _skill_status(event_type, status)
        try:
            run_index = int(envelope.get("run_index", 1))
        except (TypeError, ValueError) as exc:
            raise CollectorValidationError("run_index must be an integer") from exc
        if run_index < 1:
            raise CollectorValidationError("run_index must be >= 1")
        skill_run = {
            "skill_run_id": skill_run_id,
            "session_id": internal_session_id,
            "turn_id": turn_id,
            "skill_id": skill_id,
            "run_index": run_index,
            "activation_mode": _identifier(
                envelope.get("activation_mode"), "activation_mode"
            )
            or "unknown",
            "evidence_grade": evidence_grade,
            "confidence": confidence,
            "status": run_status,
            "started_at": occurred_at,
            "ended_at": occurred_at if event_type in TERMINAL_SKILL_EVENTS else None,
            "basis": basis,
            "source_adapter": adapter,
        }

    context = envelope.get("context") or {}
    if not isinstance(context, dict):
        raise CollectorValidationError("context must be an object")
    terminal_session = event_type in TERMINAL_SESSION_EVENTS
    session_status = (
        "failed"
        if terminal_session and status == "failed"
        else ("completed" if terminal_session else "incomplete")
    )
    session_hash = hashlib.sha256(source_session_id.encode("utf-8")).hexdigest()[:20]
    session = {
        "session_id": internal_session_id,
        "adapter": adapter,
        "adapter_version": adapter_version,
        "source_path": f"collector://{adapter}/{collection_mode}/{session_hash}",
        "source_format_version": "runtime-envelope-v1",
        "source_session_id": source_session_id,
        "correlation_key": f"{adapter}:{source_session_id}",
        "collection_mode": collection_mode,
        "transport": "local_http",
        "source_health": "active",
        "last_event_at": occurred_at,
        "title": compact_text(context.get("title") or "Live Agent runtime", 300),
        "cwd": compact_text(context.get("cwd"), 500),
        "model": compact_text(context.get("model"), 120),
        "agent_version": compact_text(context.get("agent_version"), 120),
        "started_at": occurred_at,
        "ended_at": occurred_at if terminal_session else None,
        "duration_ms": None,
        "status": session_status,
        "completeness": "complete" if terminal_session else "partial",
        "event_count": 0,
    }

    payload = redact(envelope.get("payload") or {})
    if not isinstance(payload, dict):
        payload = {"value": payload}
    payload.setdefault("source_session_id", source_session_id)
    summary = compact_text(
        envelope.get("summary")
        or payload.get("name")
        or payload.get("tool_name")
        or event_type,
        300,
    )
    source_locator = compact_text(
        source.get("record_locator") or f"collector:{event_id}", 500
    )
    parent_event_id = _identifier(envelope.get("parent_event_id"), "parent_event_id")
    event = {
        "event_id": event_id,
        "session_id": internal_session_id,
        "turn_id": turn_id,
        "skill_id": skill_id,
        "skill_run_id": skill_run_id,
        "parent_event_id": parent_event_id or None,
        "occurred_at": occurred_at,
        "event_type": event_type,
        "stage": EVENT_STAGES[event_type],
        "status": status,
        "evidence_grade": evidence_grade,
        "confidence": confidence,
        "basis": basis,
        "summary": summary,
        "source_locator": source_locator,
        "payload": payload,
    }
    raw_json = redacted_json(envelope)
    raw = {
        "raw_id": _stable_id("raw_", adapter, event_id),
        "session_id": internal_session_id,
        "adapter": adapter,
        "source_path": session["source_path"],
        "line_number": 0,
        "record_hash": hashlib.sha256(raw_json.encode("utf-8")).hexdigest(),
        "occurred_at": occurred_at,
        "record_type": event_type,
        "redacted_envelope_json": raw_json,
    }
    return {
        "session": session,
        "raw": raw,
        "event": event,
        "skill": skill_record,
        "skill_run": skill_run,
    }


def normalize_collector_payload(value: Any, limit: int = 500) -> List[Dict[str, Any]]:
    """Validate one event or a bounded batch."""
    envelopes: Iterable[Any]
    if isinstance(value, list):
        envelopes = value
    else:
        envelopes = [value]
    envelopes = list(envelopes)
    if not envelopes:
        raise CollectorValidationError("event batch must not be empty")
    if len(envelopes) > limit:
        raise CollectorValidationError(f"event batch exceeds {limit} items")
    return [normalize_collector_envelope(item) for item in envelopes]
