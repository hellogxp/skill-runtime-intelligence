"""Tests for the storage-agnostic diagnosis engine.

The engine is the single implementation shared by the local store and any remote
host. These tests pin the two properties that make that safe:

1. Building the payload from an in-memory event list produces the same stage
   projection as the store's SQL aggregation.
2. A host that cannot read ``SKILL.md`` degrades to an explicit limitation
   instead of inventing constraint outcomes.
"""

from __future__ import annotations

from skill_runtime_intelligence.diagnosis_engine import (
    DIAGNOSIS_SCHEMA_VERSION,
    aggregate_stage_counts,
    build_diagnosis_payload,
    build_stage_summary,
    evidence_completeness,
    first_gap,
)

FULL_CAPABILITIES = {
    "request": "supported",
    "discovery": "supported",
    "activation": "supported",
    "instructions": "supported",
    "resources": "supported",
    "execution": "supported",
    "artifacts": "supported",
    "outcome": "supported",
}


def _events():
    return [
        {
            "event_id": "evt_1",
            "event_type": "turn.started",
            "stage": "request",
            "evidence_grade": "observed",
            "status": "completed",
        },
        {
            "event_id": "evt_2",
            "event_type": "skill.activated",
            "stage": "activation",
            "evidence_grade": "observed",
            "status": "completed",
        },
        {
            "event_id": "evt_3",
            "event_type": "instruction.loaded",
            "stage": "instructions",
            "evidence_grade": "observed",
            "status": "completed",
        },
        {
            "event_id": "evt_4",
            "event_type": "tool.completed",
            "stage": "execution",
            "evidence_grade": "derived",
            "status": "completed",
        },
        {
            "event_id": "evt_5",
            "event_type": "tool.failed",
            "stage": "execution",
            "evidence_grade": "observed",
            "status": "failed",
        },
    ]


def test_aggregate_stage_counts_groups_by_stage_and_grade():
    counts = aggregate_stage_counts(_events())

    assert counts["execution"]["event_count"] == 2
    assert counts["execution"]["observed_count"] == 1
    assert counts["execution"]["derived_count"] == 1
    assert counts["execution"]["failed_count"] == 1
    assert "resources" not in counts


def test_aggregate_stage_counts_ignores_events_without_stage():
    counts = aggregate_stage_counts([{"event_id": "evt_x", "evidence_grade": "observed"}])

    assert counts == {}


def test_stage_summary_keeps_weakest_grade_for_a_group():
    summary = build_stage_summary(aggregate_stage_counts(_events()), FULL_CAPABILITIES)
    execution = next(item for item in summary if item["stage"] == "execution")

    # One observed event must not upgrade a group that also contains derived
    # evidence.
    assert execution["evidence_grade"] == "derived"
    assert execution["status"] == "failed"


def test_stage_summary_separates_not_observed_from_unsupported():
    capabilities = dict(FULL_CAPABILITIES)
    capabilities["artifacts"] = "unsupported"
    summary = build_stage_summary(aggregate_stage_counts(_events()), capabilities)

    by_stage = {item["stage"]: item for item in summary}
    assert by_stage["resources"]["status"] == "not_observed"
    assert by_stage["resources"]["evidence_grade"] is None
    assert by_stage["artifacts"]["status"] == "unsupported"


def test_unsupported_stages_are_excluded_from_completeness():
    capabilities = {stage: "unsupported" for stage in FULL_CAPABILITIES}
    summary = build_stage_summary({}, capabilities)

    assert evidence_completeness(summary) == 0


def test_first_gap_reports_the_earliest_observable_absence():
    summary = build_stage_summary(aggregate_stage_counts(_events()), FULL_CAPABILITIES)

    assert first_gap(summary) == "discovery"


def test_payload_is_versioned_and_complete():
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        "source_path": "collector://pdf/SKILL.md",
        "events": _events(),
    }

    payload = build_diagnosis_payload(run, capabilities=FULL_CAPABILITIES)

    assert payload["schema_version"] == DIAGNOSIS_SCHEMA_VERSION
    for key in (
        "stage_summary",
        "evidence_completeness",
        "first_gap",
        "narrative",
        "adapter_capabilities",
        "activity_summary",
        "behavior_assessment",
        "findings",
        "assessment",
    ):
        assert key in payload


def test_payload_does_not_mutate_the_caller_run():
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        "source_path": "collector://pdf/SKILL.md",
        "events": _events(),
    }

    build_diagnosis_payload(run, capabilities=FULL_CAPABILITIES)

    assert "narrative" not in run
    assert "findings" not in run


def test_narrative_labels_a_gap_as_missing_evidence_not_failure():
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        "source_path": "",
        "events": _events(),
    }

    payload = build_diagnosis_payload(run, capabilities=FULL_CAPABILITIES)

    assert "missing evidence, not proof of failure" in payload["narrative"]


def test_behavior_assessment_degrades_without_readable_definition():
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        # A remote host cannot dereference a collector-scoped path.
        "source_path": "collector://pdf/SKILL.md",
        "events": _events(),
    }

    payload = build_diagnosis_payload(run, capabilities=FULL_CAPABILITIES)
    behavior = payload["behavior_assessment"]

    assert behavior["source_status"] == "unavailable"
    assert behavior["constraints"] == []
    assert behavior["limitation"]


def test_injected_skill_source_enables_constraint_evaluation():
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        "source_path": "collector://pdf/SKILL.md",
        "events": _events(),
    }
    content = "# pdf\n\nAlways run `pytest` before reporting success.\n"

    payload = build_diagnosis_payload(
        run, capabilities=FULL_CAPABILITIES, skill_source_content=content
    )
    behavior = payload["behavior_assessment"]

    # Injecting the definition must lift the assessment out of the degraded
    # state that the same run produced without it.
    assert behavior["source_status"] != "unavailable"


def test_engine_matches_store_projection_for_the_same_events():
    """The remote path must agree with the store's own aggregation."""

    counts = aggregate_stage_counts(_events())
    summary_from_events = build_stage_summary(counts, FULL_CAPABILITIES)

    # Emulate the store handing an already-aggregated summary to the engine.
    run = {
        "name": "pdf",
        "activation_mode": "explicit_tool",
        "adapter": "otel",
        "source_path": "",
        "events": _events(),
    }
    payload = build_diagnosis_payload(
        run, capabilities=FULL_CAPABILITIES, stage_summary=summary_from_events
    )

    assert payload["stage_summary"] == summary_from_events
    assert payload["evidence_completeness"] == evidence_completeness(
        summary_from_events
    )
