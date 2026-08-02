"""Build a privacy-safe, object-level summary of one SkillRun.

The summary is deterministic presentation data. It compresses normalized
events without upgrading their evidence grade or claiming that the Skill
caused an action or outcome.
"""

from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


_GRADE_ORDER = {"observed": 0, "derived": 1, "inferred": 2, "experimental": 3}


def _weakest_grade(events: Iterable[Dict[str, Any]]) -> Optional[str]:
    grades = [
        event.get("evidence_grade")
        for event in events
        if event.get("evidence_grade") in _GRADE_ORDER
    ]
    return max(grades, key=_GRADE_ORDER.get) if grades else None


def _canonical_path(value: str, cwd: str = "") -> str:
    if not value:
        return ""
    try:
        path = Path(value).expanduser()
        if not path.is_absolute() and cwd:
            path = Path(cwd).expanduser() / path
        resolved = str(path.resolve(strict=False))
        # macOS exposes /tmp through the /private/tmp filesystem alias while
        # Linux normally keeps /tmp unchanged. Normalize both spellings into
        # one portable identity so the same source path does not become two
        # logical artifacts when evidence crosses platforms.
        private_tmp = "/private/tmp"
        if resolved == private_tmp or resolved.startswith(f"{private_tmp}/"):
            return f"/tmp{resolved[len(private_tmp):]}"
        return resolved
    except OSError:
        return str(path)


def _path_hint(canonical: Path) -> str:
    """Return a locally useful path while abbreviating the user's home."""
    try:
        relative = canonical.relative_to(Path.home())
        return str(Path("~") / relative)
    except ValueError:
        return str(canonical)


def _display_path(value: str, cwd: str) -> Dict[str, str]:
    """Return useful path identity without exposing an expanded home path."""
    if not value:
        return {
            "label": "Exact path unavailable",
            "location": "not recorded",
            "path_hint": "not recorded",
        }
    path = Path(value)
    canonical = Path(_canonical_path(value, cwd))
    if cwd:
        try:
            relative = canonical.relative_to(Path(cwd).resolve(strict=False))
            return {
                "label": str(relative),
                "location": "workspace",
                "path_hint": str(relative),
            }
        except (OSError, ValueError):
            pass
    parts = canonical.parts
    if len(parts) >= 3 and parts[1:3] == ("private", "tmp"):
        tail = Path(*parts[-3:]) if len(parts) >= 3 else path
        return {
            "label": str(tail),
            "location": "temporary",
            "path_hint": str(canonical),
        }
    if len(parts) >= 2 and parts[1] == "tmp":
        tail = Path(*parts[-3:]) if len(parts) >= 3 else path
        return {
            "label": str(tail),
            "location": "temporary",
            "path_hint": str(canonical),
        }
    tail = Path(*parts[-3:]) if len(parts) >= 3 else path
    return {
        "label": str(tail),
        "location": "external",
        "path_hint": _path_hint(canonical),
    }


def _stage_entry(
    stage: str,
    events: List[Dict[str, Any]],
    *,
    status: str,
    headline: str,
    objects: Optional[List[Dict[str, Any]]] = None,
    limitation: str = "",
) -> Dict[str, Any]:
    return {
        "stage": stage,
        "status": status,
        "headline": headline,
        "event_count": len(events),
        "evidence_grade": _weakest_grade(events),
        "event_ids": [event["event_id"] for event in events],
        "objects": objects or [],
        "limitation": limitation,
        "causal_scope": "none",
    }


def build_activity_summary(run: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize concrete resources, calls, artifacts, and outcomes."""
    events = list(run.get("events") or [])
    cwd = str(run.get("cwd") or "")
    by_stage: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for event in events:
        by_stage[str(event.get("stage") or "")].append(event)

    entries: List[Dict[str, Any]] = []

    activation = by_stage["activation"]
    if activation:
        mode = str(run.get("activation_mode") or "unknown").replace("_", " ")
        entries.append(
            _stage_entry(
                "activation",
                activation,
                status="observed",
                headline=f"Activation signal observed · {mode}",
            )
        )
    else:
        entries.append(
            _stage_entry(
                "activation",
                activation,
                status="unconfirmed",
                headline="Activation method is unconfirmed",
                limitation=(
                    "Later Skill evidence exists, but no direct activation event "
                    "identifies how the Skill entered active scope."
                ),
            )
        )

    instructions = by_stage["instructions"]
    instruction_objects = []
    for event in instructions:
        payload = event.get("payload") or {}
        path = _display_path(
            str(payload.get("file_path") or payload.get("path") or ""), cwd
        )
        if path["location"] == "not recorded":
            path = {"label": "SKILL.md", "location": "Skill directory"}
        instruction_objects.append(
            {
                **path,
                "kind": str(payload.get("resource_kind") or "skill_body"),
                "action": "loaded",
                "occurred_at": event.get("occurred_at"),
                "event_ids": [event["event_id"]],
                "evidence_grade": event.get("evidence_grade"),
                "basis": event.get("basis"),
            }
        )
    entries.append(
        _stage_entry(
            "instructions",
            instructions,
            status="observed" if instructions else "not_observed",
            headline=(
                f"{len(instruction_objects)} instruction source loaded"
                if len(instruction_objects) == 1
                else f"{len(instruction_objects)} instruction sources loaded"
            ),
            objects=instruction_objects,
            limitation=(
                "" if instructions else "No instruction-load record is available."
            ),
        )
    )

    resources = by_stage["resources"]
    resource_objects = []
    for event in resources:
        payload = event.get("payload") or {}
        path = _display_path(
            str(payload.get("file_path") or payload.get("path") or ""), cwd
        )
        resource_objects.append(
            {
                **path,
                "kind": str(payload.get("resource_kind") or "other"),
                "action": (
                    "executed"
                    if event.get("event_type") == "resource.executed"
                    else "read"
                ),
                "tool_name": payload.get("tool_name"),
                "occurred_at": event.get("occurred_at"),
                "event_ids": [event["event_id"]],
                "evidence_grade": event.get("evidence_grade"),
                "basis": event.get("basis"),
            }
        )
    entries.append(
        _stage_entry(
            "resources",
            resources,
            status="observed" if resources else "not_observed",
            headline=(
                f"{len(resource_objects)} Skill resource accessed"
                if len(resource_objects) == 1
                else f"{len(resource_objects)} Skill resources accessed"
            ),
            objects=resource_objects,
            limitation=(
                "An access was observed, but the historical normalized record "
                "does not retain the exact resource path."
                if resources
                and any(item["location"] == "not recorded" for item in resource_objects)
                else ""
            ),
        )
    )

    execution = by_stage["execution"]
    calls: Dict[str, Dict[str, Any]] = {}
    anonymous_index = 0
    for event in execution:
        payload = event.get("payload") or {}
        call_id = str(payload.get("call_id") or "")
        if not call_id:
            anonymous_index += 1
            call_id = f"anonymous-{anonymous_index}"
        call = calls.setdefault(
            call_id,
            {
                "call_id": call_id,
                "tool_name": str(payload.get("tool_name") or "unknown"),
                "started_at": None,
                "completed_at": None,
                "status": "unpaired",
                "event_ids": [],
            },
        )
        call["event_ids"].append(event["event_id"])
        event_type = str(event.get("event_type") or "")
        if event_type.endswith(("started", "requested")):
            call["started_at"] = event.get("occurred_at")
            call["status"] = "running"
        elif event_type.endswith("completed"):
            call["completed_at"] = event.get("occurred_at")
            call["status"] = "completed"
        elif event_type.endswith(("failed", "denied")):
            call["completed_at"] = event.get("occurred_at")
            call["status"] = "failed"

    tool_groups: Dict[str, Dict[str, Any]] = {}
    for call in calls.values():
        group = tool_groups.setdefault(
            call["tool_name"],
            {
                "label": call["tool_name"],
                "kind": "tool",
                "call_count": 0,
                "completed_count": 0,
                "failed_count": 0,
                "running_count": 0,
                "event_ids": [],
                "evidence_grade": "derived",
            },
        )
        group["call_count"] += 1
        group[f"{call['status']}_count"] = group.get(
            f"{call['status']}_count", 0
        ) + 1
        group["event_ids"].extend(call["event_ids"])
    execution_status = "failed" if any(
        call["status"] == "failed" for call in calls.values()
    ) else ("observed" if execution else "not_observed")
    entries.append(
        _stage_entry(
            "execution",
            execution,
            status=execution_status,
            headline=(
                f"{len(calls)} tool calls · {len(execution)} lifecycle events"
            ),
            objects=sorted(
                tool_groups.values(),
                key=lambda item: (-item["call_count"], item["label"]),
            ),
            limitation=(
                "Calls pair start and terminal records by source call ID; this "
                "is association, not a claim that the Skill caused each action."
            ),
        )
    )

    artifacts = by_stage["artifacts"]
    artifact_groups: Dict[str, Dict[str, Any]] = {}
    for event in artifacts:
        payload = event.get("payload") or {}
        raw_path = str(payload.get("path") or "")
        identity = _canonical_path(raw_path, cwd) or f"event:{event['event_id']}"
        group = artifact_groups.setdefault(
            identity,
            {
                **_display_path(raw_path, cwd),
                "kind": "artifact",
                "actions": [],
                "event_ids": [],
                "source_events": [],
            },
        )
        event_type = str(event.get("event_type") or "")
        action = event_type.split(".", 1)[-1]
        group["actions"].append(action)
        group["event_ids"].append(event["event_id"])
        group["source_events"].append(event)

    artifact_objects = []
    for group in artifact_groups.values():
        actions = group.pop("actions")
        source_events = group.pop("source_events")
        if "created" in actions and "deleted" in actions:
            final_state = "temporary · removed"
            grade = "derived"
        elif "deleted" in actions:
            final_state = "deleted"
            grade = _weakest_grade(source_events)
        elif "modified" in actions:
            final_state = "modified · retained"
            grade = _weakest_grade(source_events)
        elif "created" in actions or "produced" in actions:
            final_state = "created · retained"
            grade = _weakest_grade(source_events)
        else:
            final_state = "observed"
            grade = _weakest_grade(source_events)
        artifact_objects.append(
            {
                **group,
                "final_state": final_state,
                "evidence_grade": grade,
                "source_event_count": len(source_events),
                "observed_event_count": sum(
                    event.get("evidence_grade") == "observed"
                    for event in source_events
                ),
                "derived_event_count": sum(
                    event.get("evidence_grade") == "derived"
                    for event in source_events
                ),
                "occurred_at": source_events[-1].get("occurred_at"),
            }
        )
    artifact_objects.sort(key=lambda item: (item["location"], item["label"]))
    entries.append(
        _stage_entry(
            "artifacts",
            artifacts,
            status="observed" if artifacts else "not_observed",
            headline=(
                f"{len(artifact_objects)} logical artifacts · "
                f"{len(artifacts)} evidence records"
            ),
            objects=artifact_objects,
            limitation=(
                "Records are grouped by canonical path. Temporary create/delete "
                "pairs are shown as one logical artifact."
            ),
        )
    )

    outcome = by_stage["outcome"]
    reported = sorted([
        event for event in outcome if event.get("event_type") == "outcome.reported"
    ], key=lambda event: str(event.get("occurred_at") or ""))
    verified = [
        event for event in outcome if event.get("event_type") == "outcome.verified"
    ]
    terminal = [
        event
        for event in outcome
        if event.get("event_type") in {"turn.completed", "turn.failed"}
    ]
    final_response = reported[-1] if reported else None
    progress_reports = reported[:-1] if final_response else []
    outcome_objects = [
        {
            "label": "Final response",
            "kind": "outcome",
            "count": 1 if final_response else 0,
            "content": final_response.get("summary") if final_response else "",
            "content_scope": (
                "redacted normalized excerpt" if final_response else "unavailable"
            ),
            "occurred_at": (
                final_response.get("occurred_at") if final_response else None
            ),
            "evidence_grade": (
                final_response.get("evidence_grade") if final_response else None
            ),
            "event_ids": [final_response["event_id"]] if final_response else [],
        },
        {
            "label": "Progress updates",
            "kind": "outcome",
            "count": len(progress_reports),
            "evidence_grade": _weakest_grade(progress_reports),
            "event_ids": [event["event_id"] for event in progress_reports],
        },
        {
            "label": "Independent verification",
            "kind": "outcome",
            "count": len(verified),
            "evidence_grade": _weakest_grade(verified),
            "event_ids": [event["event_id"] for event in verified],
        },
        {
            "label": "Terminal turn signals",
            "kind": "outcome",
            "count": len(terminal),
            "evidence_grade": _weakest_grade(terminal),
            "event_ids": [event["event_id"] for event in terminal],
        },
    ]
    entries.append(
        _stage_entry(
            "outcome",
            outcome,
            status=(
                "verified"
                if verified
                else ("reported_not_verified" if reported else "not_observed")
            ),
            headline=(
                f"{1 if final_response else 0} final response · "
                f"{len(progress_reports)} progress updates · "
                f"{len(verified)} independently verified"
            ),
            objects=outcome_objects,
            limitation=(
                ""
                if verified
                else "Agent-reported completion is evidence of a report, not "
                "independent proof that the result is correct."
            ),
        )
    )

    return {
        "entries": entries,
        "discipline": (
            "Objects summarize recorded evidence. SkillRun attribution is an "
            "association and does not establish causal effectiveness."
        ),
    }
