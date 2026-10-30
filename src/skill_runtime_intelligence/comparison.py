"""Evidence-aware SkillRun comparison.

Comparison is intentionally stricter than side-by-side display.  It first
decides which dimensions are comparable, then reports differences only inside
those dimensions.  It never turns a difference into a causal claim.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


TERMINAL_STATUSES = {"completed", "failed"}
UNKNOWN_TIME_VALUES = {"", "unknown", "derived", None}


def _same_task(left: Dict[str, Any], right: Dict[str, Any]) -> bool:
    if left.get("session_id") == right.get("session_id"):
        left_turn = left.get("turn_id")
        right_turn = right.get("turn_id")
        return bool(left_turn and left_turn == right_turn) or (
            not left_turn and not right_turn
        )
    left_key = left.get("correlation_key")
    right_key = right.get("correlation_key")
    if left_key and left_key == right_key:
        left_turn = left.get("turn_id")
        right_turn = right.get("turn_id")
        return not left_turn or not right_turn or left_turn == right_turn
    return False


def _first_timestamp_event(run: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next(
        (event for event in run.get("events", []) if event.get("occurred_at")),
        None,
    )


def _time_comparability(
    left: Dict[str, Any], right: Dict[str, Any], base_comparable: bool
) -> Dict[str, str]:
    if not base_comparable:
        return {
            "status": "masked",
            "reason": "Task or Skill alignment is unavailable.",
        }
    left_event = _first_timestamp_event(left)
    right_event = _first_timestamp_event(right)
    if not left_event or not right_event:
        return {
            "status": "masked",
            "reason": "At least one run has no timestamped runtime event.",
        }
    left_origin = left_event.get("timestamp_origin")
    right_origin = right_event.get("timestamp_origin")
    left_domain = left_event.get("clock_domain")
    right_domain = right_event.get("clock_domain")
    left_uncertainty = left_event.get("clock_uncertainty_ms")
    right_uncertainty = right_event.get("clock_uncertainty_ms")
    if (
        left_origin in UNKNOWN_TIME_VALUES
        or right_origin in UNKNOWN_TIME_VALUES
        or left_domain in UNKNOWN_TIME_VALUES
        or right_domain in UNKNOWN_TIME_VALUES
        or left_uncertainty is None
        or right_uncertainty is None
    ):
        return {
            "status": "masked",
            "reason": "Timestamp provenance or clock uncertainty is unavailable.",
        }
    if left_domain != right_domain:
        return {
            "status": "masked",
            "reason": "The runs use different clock domains.",
        }
    return {
        "status": "comparable",
        "reason": (
            "Timestamp provenance, clock domain, and uncertainty are available "
            "for both runs."
        ),
    }


def _has_outcome(run: Dict[str, Any]) -> bool:
    return any(event.get("stage") == "outcome" for event in run.get("events", []))


def _dimension(
    comparable: bool, comparable_reason: str, masked_reason: str
) -> Dict[str, str]:
    return {
        "status": "comparable" if comparable else "masked",
        "reason": comparable_reason if comparable else masked_reason,
    }


def build_comparison(
    left: Dict[str, Any],
    right: Dict[str, Any],
    *,
    axis: str = "same_skill",
    task_aligned: Optional[bool] = None,
) -> Dict[str, Any]:
    """Build a dimension-masked comparison for two reconstructed SkillRuns.

    ``task_aligned=None`` preserves the original capability-only comparison for
    programmatic callers.  Product API callers pass an explicit boolean, while
    same-session or correlation evidence can still establish alignment.
    """

    axis = axis if axis in {"same_skill", "skill_version"} else "same_skill"
    observed_task_alignment = _same_task(left, right)
    legacy_capability_only = task_aligned is None
    explicit_alignment = task_aligned is True
    task_comparable = observed_task_alignment or explicit_alignment
    if legacy_capability_only:
        task_comparable = True

    same_name = left.get("name") == right.get("name")
    same_digest = left.get("digest") == right.get("digest")
    same_entrypoint = left.get("activation_mode") == right.get("activation_mode")
    skill_comparable = same_name and (
        same_digest if axis == "same_skill" else not same_digest
    )
    lifecycle_comparable = task_comparable and skill_comparable and same_entrypoint

    alignment_reasons = []
    if explicit_alignment:
        alignment_reasons.append("The user confirmed the same evaluation task.")
    elif observed_task_alignment:
        alignment_reasons.append(
            "Session, turn, or correlation evidence aligns the evaluation task."
        )
    elif legacy_capability_only:
        alignment_reasons.append(
            "Programmatic compatibility mode compares normalized capability only."
        )
    else:
        alignment_reasons.append("No shared evaluation-task evidence was observed.")
    if not same_name:
        alignment_reasons.append("Skill names differ.")
    elif axis == "same_skill" and not same_digest:
        alignment_reasons.append(
            "Skill definitions differ; select the Skill version axis to compare them."
        )
    elif axis == "skill_version" and same_digest:
        alignment_reasons.append(
            "The selected runs use the same Skill definition digest."
        )
    if not same_entrypoint:
        alignment_reasons.append("Activation entrypoints differ.")

    lifecycle_mask = _dimension(
        lifecycle_comparable,
        "Task, Skill definition, and activation entrypoint are aligned.",
        " ".join(alignment_reasons),
    )

    left_outcome_capability = left.get("adapter_capabilities", {}).get(
        "outcome", "unsupported"
    )
    right_outcome_capability = right.get("adapter_capabilities", {}).get(
        "outcome", "unsupported"
    )
    terminal = (
        left.get("status") in TERMINAL_STATUSES
        and right.get("status") in TERMINAL_STATUSES
    )
    outcome_observed = _has_outcome(left) and _has_outcome(right)
    outcome_capability = (
        "unsupported" not in {left_outcome_capability, right_outcome_capability}
        and left_outcome_capability == right_outcome_capability
    )
    outcome_comparable = (
        lifecycle_comparable and terminal and outcome_observed and outcome_capability
    )
    outcome_reasons = []
    if not lifecycle_comparable:
        outcome_reasons.append("Lifecycle alignment is unavailable.")
    if not terminal:
        outcome_reasons.append("At least one run has no terminal recorded state.")
    if not outcome_observed:
        outcome_reasons.append("At least one run has no observed outcome event.")
    if not outcome_capability:
        outcome_reasons.append("Outcome adapter capability is not equivalent.")
    outcome_mask = _dimension(
        outcome_comparable,
        "Aligned terminal runs expose equivalent outcome evidence.",
        " ".join(outcome_reasons),
    )
    time_mask = _time_comparability(left, right, lifecycle_comparable)
    comparability_mask = {
        "lifecycle": lifecycle_mask,
        "outcome": outcome_mask,
        "absolute_time": time_mask,
    }

    left_stages = {item["stage"]: item for item in left["stage_summary"]}
    right_stages = {item["stage"]: item for item in right["stage_summary"]}
    stages = []
    stage_names: Iterable[str] = left_stages.keys()
    for stage in stage_names:
        left_stage = left_stages[stage]
        right_stage = right_stages[stage]
        left_capability = left["adapter_capabilities"].get(stage, "unsupported")
        right_capability = right["adapter_capabilities"].get(stage, "unsupported")
        dimension_ready = (
            outcome_comparable if stage == "outcome" else lifecycle_comparable
        )
        if not dimension_ready:
            comparability = "alignment_limited"
            changed = None
            reason = comparability_mask[
                "outcome" if stage == "outcome" else "lifecycle"
            ]["reason"]
        elif "unsupported" in {left_capability, right_capability}:
            comparability = "unsupported"
            changed = None
            reason = "At least one adapter cannot observe this stage."
        elif left_capability != right_capability:
            comparability = "capability_limited"
            changed = None
            reason = (
                "Adapter capability differs; absence is not a behavioral difference."
            )
        else:
            comparability = "comparable"
            changed = (
                left_stage["status"] != right_stage["status"]
                or left_stage["event_count"] != right_stage["event_count"]
            )
            reason = (
                "Comparable normalized evidence differs."
                if changed
                else "Comparable normalized evidence agrees."
            )
        stages.append(
            {
                "stage": stage,
                "comparability": comparability,
                "changed": changed,
                "reason": reason,
                "left": left_stage,
                "right": right_stage,
            }
        )

    statuses = {item["status"] for item in comparability_mask.values()}
    decision = (
        "comparable"
        if statuses == {"comparable"}
        else "partially_comparable"
        if "comparable" in statuses
        else "not_comparable"
    )
    return {
        "axis": axis,
        "decision": decision,
        "comparability_mask": comparability_mask,
        "alignment_basis": " ".join(alignment_reasons),
        "stages": stages,
        "same_skill_name": same_name,
        "same_skill_digest": same_digest,
        "same_entrypoint": same_entrypoint,
        "task_aligned": task_comparable,
        "causal_attribution_allowed": False,
    }
