"""Opt-in, fail-open OTLP/HTTP JSON export for Skill runtime evidence."""

import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .redaction import compact_text
from .storage import Storage


OTLP_EXPORTER_VERSION = "0.1.0"


def normalize_otlp_endpoint(endpoint: str) -> str:
    value = str(endpoint or "").strip().rstrip("/")
    if not value:
        raise ValueError("OTLP endpoint is required")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("OTLP endpoint must be an http(s) URL")
    if not parsed.path or parsed.path == "/":
        value += "/v1/traces"
    elif not parsed.path.endswith("/v1/traces"):
        value += "/v1/traces"
    return value


def public_endpoint(endpoint: str) -> str:
    parsed = urlsplit(normalize_otlp_endpoint(endpoint))
    host = parsed.hostname or ""
    if parsed.port:
        host = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme, host, parsed.path, "", ""))


def _stable_hex(length: int, *parts: Any) -> str:
    value = "\0".join(str(part or "") for part in parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:length]


def _timestamp_nanos(value: Any) -> str:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        parsed = datetime.now(timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return str(int(parsed.timestamp() * 1_000_000_000))


def _attribute(key: str, value: Any) -> Dict[str, Any]:
    if isinstance(value, bool):
        encoded = {"boolValue": value}
    elif isinstance(value, int):
        encoded = {"intValue": str(value)}
    elif isinstance(value, float):
        encoded = {"doubleValue": value}
    else:
        encoded = {"stringValue": compact_text(value, 500)}
    return {"key": key, "value": encoded}


def event_to_otlp_span(event: Dict[str, Any]) -> Dict[str, Any]:
    start = _timestamp_nanos(event.get("occurred_at"))
    payload = {}
    try:
        payload = json.loads(event.get("payload_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        pass
    duration_ms = payload.get("duration_ms")
    try:
        duration_nanos = max(0, int(float(duration_ms) * 1_000_000))
    except (TypeError, ValueError):
        duration_nanos = 1
    attributes = [
        _attribute("skill.runtime.event_id", event["event_id"]),
        _attribute("skill.runtime.event", event["event_type"]),
        _attribute("skill.runtime.stage", event["stage"]),
        _attribute("skill.runtime.evidence.grade", event["evidence_grade"]),
        _attribute("skill.runtime.evidence.confidence", event["confidence"]),
        _attribute("skill.runtime.source.adapter", event["adapter"]),
        _attribute("skill.runtime.source.adapter_version", event["adapter_version"]),
        _attribute("skill.runtime.collection.session_id", event["source_session_id"]),
        _attribute("skill.runtime.status", event["status"]),
    ]
    if event.get("skill_name"):
        attributes.append(_attribute("skill.runtime.name", event["skill_name"]))
    if event.get("skill_run_id"):
        attributes.append(
            _attribute("skill.runtime.run_id", event["skill_run_id"])
        )
    if event.get("turn_id"):
        attributes.append(_attribute("skill.runtime.turn_id", event["turn_id"]))
    return {
        "traceId": _stable_hex(32, "session", event["session_id"]),
        "spanId": _stable_hex(16, "event", event["event_id"]),
        "parentSpanId": (
            _stable_hex(16, "event", event["parent_event_id"])
            if event.get("parent_event_id")
            else ""
        ),
        "name": f"skill.runtime.{event['event_type']}",
        "kind": 1,
        "startTimeUnixNano": start,
        "endTimeUnixNano": str(int(start) + max(1, duration_nanos)),
        "attributes": attributes,
        "status": {
            "code": 2 if event["status"] == "failed" else 1,
            "message": "runtime evidence reported failure"
            if event["status"] == "failed"
            else "",
        },
    }


def build_otlp_payload(events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    spans = [event_to_otlp_span(event) for event in events]
    return {
        "resourceSpans": [
            {
                "resource": {
                    "attributes": [
                        _attribute("service.name", "skill-runtime-intelligence"),
                        _attribute("service.version", OTLP_EXPORTER_VERSION),
                        _attribute("telemetry.sdk.language", "python"),
                    ]
                },
                "scopeSpans": [
                    {
                        "scope": {
                            "name": "skill-runtime-intelligence",
                            "version": OTLP_EXPORTER_VERSION,
                        },
                        "spans": spans,
                    }
                ],
            }
        ]
    }


def _checkpoint_key(endpoint: str) -> str:
    digest = hashlib.sha256(
        public_endpoint(endpoint).encode("utf-8")
    ).hexdigest()[:16]
    return f"export.otlp.{digest}.checkpoint"


def _status_key(endpoint: str) -> str:
    digest = hashlib.sha256(
        public_endpoint(endpoint).encode("utf-8")
    ).hexdigest()[:16]
    return f"export.otlp.{digest}.status"


def _send(
    endpoint: str,
    payload: Dict[str, Any],
    headers: Optional[Dict[str, str]] = None,
    timeout_seconds: float = 3.0,
) -> None:
    request_headers = {
        "Content-Type": "application/json",
        "User-Agent": f"skill-runtime-intelligence/{OTLP_EXPORTER_VERSION}",
    }
    request_headers.update(headers or {})
    request = Request(
        normalize_otlp_endpoint(endpoint),
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    with urlopen(request, timeout=max(0.1, timeout_seconds)) as response:
        response.read(4096)
        if not 200 <= response.status < 300:
            raise RuntimeError(f"OTLP endpoint returned HTTP {response.status}")


def export_otlp_once(
    database: Path,
    endpoint: str,
    headers: Optional[Dict[str, str]] = None,
    batch_size: int = 200,
    timeout_seconds: float = 3.0,
) -> Dict[str, Any]:
    endpoint = normalize_otlp_endpoint(endpoint)
    storage = Storage(database)
    status = {
        "type": "otlp_http_json",
        "version": OTLP_EXPORTER_VERSION,
        "endpoint": public_endpoint(endpoint),
        "enabled": True,
        "last_attempt_at": datetime.now(timezone.utc).isoformat(),
        "last_success_at": None,
        "last_error": "",
        "exported": 0,
        "pending": False,
    }
    try:
        checkpoint_key = _checkpoint_key(endpoint)
        checkpoint = int(storage.runtime_state(checkpoint_key, "0") or 0)
        events = storage.export_events_after(checkpoint, batch_size)
        if not events:
            status["last_success_at"] = status["last_attempt_at"]
            storage.set_runtime_state(_status_key(endpoint), json.dumps(status))
            return status
        _send(endpoint, build_otlp_payload(events), headers, timeout_seconds)
        checkpoint = int(events[-1]["export_row_id"])
        storage.set_runtime_state(checkpoint_key, str(checkpoint))
        status["exported"] = len(events)
        status["last_success_at"] = datetime.now(timezone.utc).isoformat()
        status["pending"] = len(events) >= batch_size
    except (HTTPError, URLError, TimeoutError, OSError, RuntimeError, ValueError) as exc:
        status["last_error"] = compact_text(str(exc), 240)
        status["pending"] = True
    finally:
        storage.set_runtime_state(_status_key(endpoint), json.dumps(status))
        storage.close()
    return status


def watch_otlp_export(
    database: Path,
    endpoint: str,
    headers: Optional[Dict[str, str]] = None,
    interval_seconds: float = 2.0,
    batch_size: int = 200,
) -> None:
    while True:
        result = export_otlp_once(
            database,
            endpoint,
            headers=headers,
            batch_size=batch_size,
        )
        delay = 0.05 if result.get("exported") and result.get("pending") else interval_seconds
        time.sleep(max(0.05, delay))
