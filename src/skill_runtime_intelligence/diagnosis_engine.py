"""Storage-agnostic Skill runtime diagnosis engine.

This module is the single implementation of the diagnosis projection. Both the
local SRI store and any remote host (for example a server that receives
normalized events over OTLP) call the same functions here, so evidence
semantics cannot diverge between deployments.

Design rules:

1. Pure functions only. No filesystem, database, or network access.
2. Input is a run dictionary plus its normalized events. Nothing in this module
   knows who renders the result.
3. Absent evidence is reported as ``not_observed`` or ``unsupported``. The
   engine never invents an observation to fill a gap.
4. The payload is versioned. Consumers must check ``schema_version``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from .activity_summary import build_activity_summary
from .behavior_constraints import assess_skill_behavior
from .diagnostics import assess_skill_run, diagnose_skill_run

#: Versioned contract identifier for the diagnosis payload.
DIAGNOSIS_SCHEMA_VERSION = "skill.runtime.diagnosis/1"

STAGES = (
    "request",
    "discovery",
    "activation",
    "instructions",
    "resources",
    "execution",
    "artifacts",
    "outcome",
)

_GRADE_ORDER = ("observed", "derived", "inferred")


def aggregate_stage_counts(events: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Group normalized events by lifecycle stage.

    This replaces the store's SQL ``GROUP BY`` so the same summary can be built
    from an in-memory event list. Callers must pass events already scoped to one
    Skill run; this function does not perform attribution.
    """

    by_stage: Dict[str, Dict[str, Any]] = {}
    for event in events:
        stage = event.get("stage")
        if not stage:
            continue
        bucket = by_stage.setdefault(
            stage,
            {
                "event_count": 0,
                "observed_count": 0,
                "derived_count": 0,
                "inferred_count": 0,
                "failed_count": 0,
            },
        )
        bucket["event_count"] += 1
        grade = event.get("evidence_grade")
        if grade in _GRADE_ORDER:
            bucket[f"{grade}_count"] += 1
        if event.get("status") == "failed":
            bucket["failed_count"] += 1
    return by_stage


def build_stage_summary(
    by_stage: Dict[str, Dict[str, Any]], capabilities: Dict[str, str]
) -> List[Dict[str, Any]]:
    """Project per-stage counts into the lifecycle summary rendered by a UI."""

    result: List[Dict[str, Any]] = []
    for stage in STAGES:
        values = by_stage.get(stage) or {}
        count = int(values.get("event_count") or 0)
        capability = capabilities.get(stage, "unsupported")
        if count:
            status = "failed" if values.get("failed_count") else "observed"
            grades = [
                grade for grade in _GRADE_ORDER if values.get(f"{grade}_count")
            ]
            # A stage badge summarizes the whole group, so retain the weakest
            # evidence grade instead of allowing one direct event to make
            # derived or inferred records look observed.
            grade = grades[-1] if grades else "observed"
        elif capability == "unsupported":
            status = "unsupported"
            grade = None
        else:
            status = "not_observed"
            grade = None
        result.append(
            {
                "stage": stage,
                "status": status,
                "capability": capability,
                "event_count": count,
                "evidence_grade": grade,
            }
        )
    return result


def evidence_completeness(stage_summary: List[Dict[str, Any]]) -> int:
    """Percentage of observable stages that carry at least one event."""

    observable = [
        stage for stage in stage_summary if stage["capability"] != "unsupported"
    ]
    if not observable:
        return 0
    observed = sum(stage["event_count"] > 0 for stage in observable)
    return round(observed * 100 / len(observable))


def first_gap(stage_summary: List[Dict[str, Any]]) -> Optional[str]:
    """First stage that is observable but has no evidence."""

    for stage in stage_summary:
        if stage["status"] == "not_observed":
            return stage["stage"]
    return None


def narrative(run: Dict[str, Any]) -> str:
    """Human-readable run summary assembled only from evidence-backed counts."""

    counts = {item["stage"]: item["event_count"] for item in run["stage_summary"]}
    fragments = [f"Skill `{run['name']}` has runtime evidence in this run."]
    if counts.get("activation"):
        fragments.append(f"Activation evidence: {counts['activation']}.")
    elif run.get("activation_mode") == "unknown":
        fragments.append("Activation mode was not exposed by the source.")
    if counts.get("instructions"):
        fragments.append("Its primary instructions were loaded.")
    if counts.get("resources"):
        fragments.append(
            f"{counts['resources']} resource access event(s) were observed."
        )
    if counts.get("execution"):
        fragments.append(
            f"{counts['execution']} execution event(s) were attributed."
        )
    if counts.get("artifacts"):
        fragments.append(
            f"{counts['artifacts']} file or artifact event(s) were connected."
        )
    if run.get("first_gap"):
        fragments.append(
            f"The first observable lifecycle gap is `{run['first_gap']}`; "
            "this is missing evidence, not proof of failure."
        )
    return " ".join(fragments)


def build_diagnosis_payload(
    run: Dict[str, Any],
    *,
    capabilities: Dict[str, str],
    events: Optional[Iterable[Dict[str, Any]]] = None,
    stage_summary: Optional[List[Dict[str, Any]]] = None,
    skill_source_content: Optional[str] = None,
) -> Dict[str, Any]:
    """Build the complete, versioned diagnosis payload for one Skill run.

    ``run`` must contain at least ``name`` and ``events``. Provide either
    ``stage_summary`` (when a store already aggregated it) or ``events``/
    ``run["events"]`` so the summary can be aggregated here.

    ``skill_source_content`` is the current ``SKILL.md`` text. Remote hosts that
    cannot read the author's filesystem may omit it; behaviour assessment then
    reports its own ``limitation`` instead of guessing constraint outcomes.
    """

    scoped_events = events if events is not None else run.get("events") or []
    if stage_summary is None:
        stage_summary = build_stage_summary(
            aggregate_stage_counts(scoped_events), capabilities
        )

    projected = dict(run)
    projected["stage_summary"] = stage_summary
    projected["evidence_completeness"] = evidence_completeness(stage_summary)
    projected["first_gap"] = first_gap(stage_summary)
    projected["narrative"] = narrative(projected)
    projected["adapter_capabilities"] = dict(capabilities)
    projected["activity_summary"] = build_activity_summary(projected)
    projected["behavior_assessment"] = assess_skill_behavior(
        projected, source_content=skill_source_content
    )
    projected["findings"] = diagnose_skill_run(projected)
    projected["assessment"] = assess_skill_run(projected, projected["findings"])

    return {
        "schema_version": DIAGNOSIS_SCHEMA_VERSION,
        "stage_summary": projected["stage_summary"],
        "evidence_completeness": projected["evidence_completeness"],
        "first_gap": projected["first_gap"],
        "narrative": projected["narrative"],
        "adapter_capabilities": projected["adapter_capabilities"],
        "activity_summary": projected["activity_summary"],
        "behavior_assessment": projected["behavior_assessment"],
        "findings": projected["findings"],
        "assessment": projected["assessment"],
    }
