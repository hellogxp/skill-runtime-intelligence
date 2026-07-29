"""Import adapter for mainstream trace/observability exports.

OpenTelemetry is the canonical interchange model. Vendor profiles only map
their exported span/call records into that model; Skill semantics remain an
explicit extension and are never guessed from a span name.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from ..discovery import SkillDefinition
from ..redaction import compact_text, redact, redacted_json
from .codex import _stable_id


ADAPTER_VERSION = "0.1.0"
SUPPORTED_PROFILES = ("otel", "langfuse", "langsmith", "phoenix", "weave", "datadog")
SKILL_ATTRIBUTE_KEYS = (
    "skill.runtime.name",
    "sri.skill.name",
    "gen_ai.skill.name",
    "agent.skill.name",
    "skill.name",
    "skill_name",
    "related_skill_name",
    "skill",
)


def _value(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    for key in (
        "stringValue",
        "intValue",
        "doubleValue",
        "boolValue",
        "bytesValue",
    ):
        if key in value:
            return value[key]
    if "arrayValue" in value:
        values = value["arrayValue"].get("values", [])
        return [_value(item) for item in values]
    if "kvlistValue" in value:
        return _attributes(value["kvlistValue"].get("values", []))
    return value


def _attributes(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return {str(key): _value(item) for key, item in value.items()}
    if isinstance(value, list):
        result = {}
        for item in value:
            if isinstance(item, dict) and "key" in item:
                result[str(item["key"])] = _value(item.get("value"))
        return result
    return {}


def _flatten_attributes(value: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
    result = {}
    for key, item in value.items():
        path = f"{prefix}.{key}" if prefix else str(key)
        result[path] = item
        if isinstance(item, dict):
            result.update(_flatten_attributes(item, path))
    return result


def _timestamp(value: Any) -> Optional[str]:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        if value.isdigit():
            value = int(value)
        else:
            return value
    if isinstance(value, (int, float)):
        number = float(value)
        if number > 1e16:
            number /= 1e9
        elif number > 1e13:
            number /= 1e6
        elif number > 1e10:
            number /= 1e3
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    return None


def _duration_ms(start: Optional[str], end: Optional[str]) -> Optional[int]:
    if not start or not end:
        return None
    try:
        start_time = datetime.fromisoformat(start.replace("Z", "+00:00"))
        end_time = datetime.fromisoformat(end.replace("Z", "+00:00"))
    except ValueError:
        return None
    return max(0, int((end_time - start_time).total_seconds() * 1000))


def _status(value: Any, error: Any = None) -> str:
    if error:
        return "failed"
    if isinstance(value, dict):
        value = value.get("code") or value.get("status_code")
    normalized = str(value or "").casefold()
    if normalized in {"error", "failed", "status_code_error", "2"}:
        return "failed"
    if normalized in {"cancelled", "canceled", "interrupted"}:
        return "interrupted"
    return "completed"


def _skill_name(span: Dict[str, Any]) -> Optional[str]:
    attributes = _flatten_attributes(span.get("attributes", {}))
    for key in SKILL_ATTRIBUTE_KEYS:
        value = attributes.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    if str(span.get("kind") or "").casefold() == "skill":
        return str(span.get("name") or "").strip() or None
    return None


def _external_skill(profile: str, name: str) -> SkillDefinition:
    source_path = f"observability://{profile}/{name}"
    digest = hashlib.sha256(source_path.encode("utf-8")).hexdigest()
    return SkillDefinition(
        skill_id=f"skill_{digest[:20]}",
        name=name,
        description=f"Skill observed through the {profile} import adapter",
        source_kind="external",
        source_path=source_path,
        digest=digest,
        valid=True,
        validation_message="Runtime-only definition; local SKILL.md not imported",
    )


class ObservabilityAdapter:
    version = ADAPTER_VERSION

    def __init__(self, source_path: Path, profile: str = "auto"):
        self.source_path = source_path.expanduser().resolve()
        self.requested_profile = profile

    def parse(
        self,
    ) -> Tuple[List[SkillDefinition], List[Tuple[dict, list, list, list]], str]:
        document = json.loads(self.source_path.read_text(encoding="utf-8"))
        profile = self._detect_profile(document)
        spans = list(self._spans(document, profile))
        by_trace: Dict[str, List[Dict[str, Any]]] = {}
        for index, span in enumerate(spans, 1):
            trace_id = str(span.get("trace_id") or span.get("id") or f"trace-{index}")
            span["trace_id"] = trace_id
            span["_index"] = index
            by_trace.setdefault(trace_id, []).append(span)

        definitions: Dict[str, SkillDefinition] = {}
        bundles = []
        for trace_id, trace_spans in by_trace.items():
            names = sorted(
                {name for name in (_skill_name(span) for span in trace_spans) if name}
            )
            if not names:
                continue
            for name in names:
                definitions.setdefault(name, _external_skill(profile, name))
            bundles.append(
                self._trace_bundle(
                    profile,
                    trace_id,
                    trace_spans,
                    {name: definitions[name] for name in names},
                )
            )
        return list(definitions.values()), bundles, profile

    def _detect_profile(self, document: Any) -> str:
        if self.requested_profile != "auto":
            if self.requested_profile not in SUPPORTED_PROFILES:
                raise ValueError(f"Unsupported observability profile: {self.requested_profile}")
            return self.requested_profile
        if isinstance(document, dict):
            if "resourceSpans" in document:
                return "otel"
            if "observations" in document or (
                isinstance(document.get("data"), list)
                and any("traceId" in item for item in document.get("data", []) if isinstance(item, dict))
            ):
                return "langfuse"
            if "calls" in document:
                return "weave"
            data = document.get("data")
            if isinstance(data, list) and any(
                isinstance(item, dict)
                and isinstance(item.get("attributes"), dict)
                and "span_id" in item["attributes"]
                for item in data
            ):
                return "datadog"
            if "runs" in document:
                return "langsmith"
        if isinstance(document, list):
            if any(isinstance(item, dict) and "run_type" in item for item in document):
                return "langsmith"
            if any(isinstance(item, dict) and "op_name" in item for item in document):
                return "weave"
        return "otel"

    def _spans(self, document: Any, profile: str) -> Iterable[Dict[str, Any]]:
        if profile in {"otel", "phoenix"}:
            yield from self._otel_spans(document)
        elif profile == "langsmith":
            yield from self._langsmith_spans(document)
        elif profile == "langfuse":
            yield from self._langfuse_spans(document)
        elif profile == "weave":
            yield from self._weave_spans(document)
        elif profile == "datadog":
            yield from self._datadog_spans(document)

    def _otel_spans(self, document: Any) -> Iterable[Dict[str, Any]]:
        roots = document.get("resourceSpans", []) if isinstance(document, dict) else []
        for resource_span in roots:
            resource = _attributes(resource_span.get("resource", {}).get("attributes", []))
            scopes = resource_span.get("scopeSpans") or resource_span.get("instrumentationLibrarySpans") or []
            for scope in scopes:
                for span in scope.get("spans", []):
                    attrs = {**resource, **_attributes(span.get("attributes", []))}
                    yield {
                        "id": span.get("spanId"),
                        "trace_id": span.get("traceId"),
                        "parent_id": span.get("parentSpanId"),
                        "name": span.get("name") or "OTel span",
                        "kind": attrs.get("openinference.span.kind")
                        or attrs.get("gen_ai.operation.name")
                        or span.get("kind"),
                        "start": _timestamp(span.get("startTimeUnixNano")),
                        "end": _timestamp(span.get("endTimeUnixNano")),
                        "status": _status(span.get("status")),
                        "attributes": attrs,
                    }

    def _langsmith_spans(self, document: Any) -> Iterable[Dict[str, Any]]:
        runs = document if isinstance(document, list) else document.get("runs", document.get("data", []))
        for run in runs:
            if not isinstance(run, dict):
                continue
            extra = _attributes(run.get("extra", {}))
            metadata = _attributes(extra.get("metadata", {}))
            yield {
                "id": run.get("id"),
                "trace_id": run.get("trace_id") or run.get("traceId") or run.get("id"),
                "parent_id": run.get("parent_run_id") or run.get("parent_id"),
                "name": run.get("name") or "LangSmith run",
                "kind": run.get("run_type"),
                "start": _timestamp(run.get("start_time")),
                "end": _timestamp(run.get("end_time")),
                "status": _status(run.get("status"), run.get("error")),
                "attributes": {**extra, **metadata, **_attributes(run.get("metadata", {}))},
            }

    def _langfuse_spans(self, document: Any) -> Iterable[Dict[str, Any]]:
        observations = (
            document
            if isinstance(document, list)
            else document.get("observations", document.get("data", []))
        )
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            attrs = {
                **_attributes(observation.get("metadata", {})),
                **_attributes(observation.get("attributes", {})),
            }
            yield {
                "id": observation.get("id"),
                "trace_id": observation.get("traceId")
                or observation.get("trace_id")
                or observation.get("id"),
                "parent_id": observation.get("parentObservationId")
                or observation.get("parent_observation_id"),
                "name": observation.get("name") or "Langfuse observation",
                "kind": observation.get("type") or observation.get("observationType"),
                "start": _timestamp(observation.get("startTime") or observation.get("start_time")),
                "end": _timestamp(observation.get("endTime") or observation.get("end_time")),
                "status": _status(observation.get("level"), observation.get("statusMessage")),
                "attributes": attrs,
            }

    def _weave_spans(self, document: Any) -> Iterable[Dict[str, Any]]:
        calls = document if isinstance(document, list) else document.get("calls", document.get("data", []))
        for call in calls:
            if not isinstance(call, dict):
                continue
            yield {
                "id": call.get("id"),
                "trace_id": call.get("trace_id") or call.get("id"),
                "parent_id": call.get("parent_id"),
                "name": call.get("display_name") or call.get("op_name") or "Weave call",
                "kind": call.get("span_kind") or call.get("kind") or "call",
                "start": _timestamp(call.get("started_at")),
                "end": _timestamp(call.get("ended_at")),
                "status": _status(call.get("status"), call.get("exception")),
                "attributes": _attributes(call.get("attributes", {})),
            }

    def _datadog_spans(self, document: Any) -> Iterable[Dict[str, Any]]:
        data = document if isinstance(document, list) else document.get("data", [])
        for item in data:
            if not isinstance(item, dict):
                continue
            attrs = _attributes(item.get("attributes", {}))
            meta = _attributes(attrs.get("meta", {}))
            start = _timestamp(attrs.get("start") or attrs.get("start_ns"))
            end = _timestamp(attrs.get("end") or attrs.get("end_ns"))
            if not end and start and attrs.get("duration"):
                try:
                    start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
                    end = datetime.fromtimestamp(
                        start_dt.timestamp() + float(attrs["duration"]) / 1e9,
                        tz=timezone.utc,
                    ).isoformat().replace("+00:00", "Z")
                except (TypeError, ValueError):
                    pass
            yield {
                "id": attrs.get("span_id") or item.get("id"),
                "trace_id": attrs.get("trace_id") or item.get("id"),
                "parent_id": attrs.get("parent_id"),
                "name": attrs.get("name") or attrs.get("span_name") or "Datadog span",
                "kind": meta.get("span.kind") or attrs.get("span_kind"),
                "start": start,
                "end": end,
                "status": _status(attrs.get("status"), attrs.get("error")),
                "attributes": {**attrs, **meta},
            }

    def _trace_bundle(
        self,
        profile: str,
        trace_id: str,
        spans: List[Dict[str, Any]],
        definitions: Dict[str, SkillDefinition],
    ) -> Tuple[dict, list, list, list]:
        spans.sort(key=lambda item: (item.get("start") or "", item.get("_index", 0)))
        by_id = {str(span.get("id")): span for span in spans if span.get("id")}
        explicit_by_span = {
            str(span.get("id")): _skill_name(span)
            for span in spans
            if span.get("id") and _skill_name(span)
        }

        def inherited_skill(span: Dict[str, Any]) -> Tuple[Optional[str], str]:
            direct = _skill_name(span)
            if direct:
                return direct, "observed"
            parent_id = str(span.get("parent_id") or "")
            visited = set()
            while parent_id and parent_id not in visited:
                visited.add(parent_id)
                if explicit_by_span.get(parent_id):
                    return explicit_by_span[parent_id], "derived"
                parent = by_id.get(parent_id)
                parent_id = str(parent.get("parent_id") or "") if parent else ""
            return None, "unattributed"

        source_string = str(self.source_path)
        session_id = _stable_id("session", profile, trace_id, source_string)
        start_event_types = {}
        for span in spans:
            span_id = str(span.get("id") or f"span-{span['_index']}")
            name, attribution_grade = inherited_skill(span)
            explicit_event = _flatten_attributes(span.get("attributes", {})).get(
                "skill.runtime.event"
            )
            if explicit_event:
                start_event_types[span_id] = str(explicit_event)
            elif name and attribution_grade == "observed":
                start_event_types[span_id] = "skill.activated"
            else:
                start_event_types[span_id] = (
                    "tool.started"
                    if str(span.get("kind") or "").casefold() == "tool"
                    else "runtime.span.started"
                )
        raw = []
        events = []
        runs: Dict[str, Dict[str, Any]] = {}
        first_start = spans[0].get("start") if spans else None
        last_end = max((span.get("end") or "" for span in spans), default="") or None

        for span in spans:
            index = int(span["_index"])
            span_id = str(span.get("id") or f"span-{index}")
            name, attribution_grade = inherited_skill(span)
            definition = definitions.get(name or "")
            run_id = (
                _stable_id("skillrun", session_id, definition.skill_id)
                if definition
                else None
            )
            if definition and run_id not in runs:
                runs[run_id] = {
                    "skill_run_id": run_id,
                    "session_id": session_id,
                    "turn_id": trace_id,
                    "skill_id": definition.skill_id,
                    "run_index": 1,
                    "activation_mode": (
                        "explicit_attribute"
                        if attribution_grade == "observed"
                        else "inherited_span_scope"
                    ),
                    "evidence_grade": attribution_grade,
                    "confidence": 1.0,
                    "status": span["status"],
                    "started_at": span.get("start"),
                    "ended_at": span.get("end"),
                    "basis": (
                        f"{profile} span carries an explicit Skill attribute"
                        if attribution_grade == "observed"
                        else "Skill attribution inherited through span ancestry"
                    ),
                    "source_adapter": profile,
                }
            elif run_id:
                run = runs[run_id]
                starts = [
                    value
                    for value in (run.get("started_at"), span.get("start"))
                    if value
                ]
                ends = [
                    value
                    for value in (run.get("ended_at"), span.get("end"))
                    if value
                ]
                run["started_at"] = min(starts) if starts else None
                run["ended_at"] = max(ends) if ends else None
                if span["status"] == "failed":
                    run["status"] = "failed"

            raw.append(
                {
                    "raw_id": _stable_id("raw", session_id, span_id),
                    "session_id": session_id,
                    "adapter": profile,
                    "source_path": source_string,
                    "line_number": index,
                    "record_hash": hashlib.sha256(
                        json.dumps(span, sort_keys=True, default=str).encode("utf-8")
                    ).hexdigest(),
                    "occurred_at": span.get("start"),
                    "record_type": str(span.get("kind") or "span"),
                    "redacted_envelope_json": redacted_json(
                        {
                            "span_id": span_id,
                            "trace_id": trace_id,
                            "parent_id": span.get("parent_id"),
                            "name": compact_text(span.get("name"), 100),
                            "kind": span.get("kind"),
                            "attribute_keys": sorted(span.get("attributes", {}).keys()),
                        }
                    ),
                }
            )
            if not definition or not run_id:
                continue

            explicit_event = _flatten_attributes(span.get("attributes", {})).get(
                "skill.runtime.event"
            )
            if explicit_event:
                event_type = start_event_types[span_id]
                stage = str(
                    _flatten_attributes(span.get("attributes", {})).get(
                        "skill.runtime.stage", "execution"
                    )
                )
            elif attribution_grade == "observed":
                event_type = start_event_types[span_id]
                stage = "activation"
            else:
                event_type = start_event_types[span_id]
                stage = "execution"
            parent_span_id = str(span.get("parent_id") or "")
            parent_event_id = (
                _stable_id(
                    "evt",
                    session_id,
                    parent_span_id,
                    start_event_types.get(
                        parent_span_id, "runtime.span.started"
                    ),
                )
                if parent_span_id
                else None
            )
            start_event_id = _stable_id("evt", session_id, span_id, event_type)
            events.append(
                self._event(
                    session_id,
                    trace_id,
                    run_id,
                    definition.skill_id,
                    span_id,
                    parent_event_id,
                    span.get("start"),
                    event_type,
                    stage,
                    span["status"],
                    "observed",
                    f"{profile} exported span",
                    f"{span.get('name') or 'Runtime span'} started",
                    index,
                )
            )
            events.append(
                self._event(
                    session_id,
                    trace_id,
                    run_id,
                    definition.skill_id,
                    span_id + ":end",
                    start_event_id,
                    span.get("end"),
                    (
                        "tool.completed"
                        if str(span.get("kind") or "").casefold() == "tool"
                        else "runtime.span.completed"
                    ),
                    "execution",
                    span["status"],
                    "derived",
                    "End event deterministically derived from exported span duration/status",
                    f"{span.get('name') or 'Runtime span'} {span['status']}",
                    index,
                )
            )

        root_name = next(
            (span.get("name") for span in spans if not span.get("parent_id")),
            f"{profile} trace {trace_id[:12]}",
        )
        session_status = (
            "failed" if any(span["status"] == "failed" for span in spans) else "completed"
        )
        session = {
            "session_id": session_id,
            "adapter": profile,
            "adapter_version": self.version,
            "source_path": f"{source_string}#{trace_id}",
            "source_format_version": f"{profile}-export",
            "title": compact_text(root_name, 100) or f"{profile} trace",
            "cwd": "",
            "model": "",
            "agent_version": "",
            "started_at": first_start,
            "ended_at": last_end,
            "duration_ms": _duration_ms(first_start, last_end),
            "status": session_status,
            "completeness": "complete" if last_end else "incomplete",
            "event_count": len(events),
        }
        return session, raw, events, list(runs.values())

    def _event(
        self,
        session_id: str,
        turn_id: str,
        skill_run_id: str,
        skill_id: str,
        span_id: str,
        parent_event_id: Optional[str],
        occurred_at: Optional[str],
        event_type: str,
        stage: str,
        status: str,
        evidence_grade: str,
        basis: str,
        summary: str,
        index: int,
    ) -> Dict[str, Any]:
        return {
            "event_id": _stable_id("evt", session_id, span_id, event_type),
            "session_id": session_id,
            "turn_id": turn_id,
            "skill_id": skill_id,
            "skill_run_id": skill_run_id,
            "parent_event_id": parent_event_id,
            "occurred_at": occurred_at,
            "event_type": event_type,
            "stage": stage if stage in {
                "request",
                "discovery",
                "activation",
                "instructions",
                "resources",
                "execution",
                "artifacts",
                "outcome",
            } else "execution",
            "status": status,
            "evidence_grade": evidence_grade,
            "confidence": 1.0,
            "basis": basis,
            "summary": compact_text(summary, 220),
            "source_locator": f"{self.source_path}:span:{span_id or index}",
            "payload": redact({"span_id": span_id, "source_profile": self.requested_profile}),
        }
