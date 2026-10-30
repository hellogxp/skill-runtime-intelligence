"""Evidence-graded diagnostics for reconstructed SkillRuns.

The rules in this module are intentionally deterministic. They diagnose the
observable runtime record; they do not claim access to the model's hidden
reasoning or causal Skill effectiveness.
"""

import hashlib
from typing import Any, Dict, Iterable, List, Optional


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
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGES)}
CAUSAL_SCOPES = (
    "none",
    "source_assertion_only",
    "experimental_estimate",
)
CAUSAL_CLAIM_KINDS = (
    "descriptive",
    "source_attribution",
    "skill_outcome_effect",
)
_ALLOWED_CAUSAL_CLAIMS = {
    "none": {"descriptive"},
    "source_assertion_only": {"descriptive", "source_attribution"},
    "experimental_estimate": set(CAUSAL_CLAIM_KINDS),
}


def validate_causal_claim(causal_scope: str, claim_kind: str) -> Dict[str, Any]:
    """Fail closed when a claim exceeds its evidence-backed causal scope."""
    allowed_claims = _ALLOWED_CAUSAL_CLAIMS.get(causal_scope, set())
    allowed = claim_kind in allowed_claims
    if allowed:
        reason = "The requested claim is within the finding's causal scope."
    elif causal_scope not in CAUSAL_SCOPES:
        reason = "Unknown causal scope; causal attribution is denied."
    elif claim_kind not in CAUSAL_CLAIM_KINDS:
        reason = "Unknown claim kind; causal attribution is denied."
    else:
        reason = (
            f"{causal_scope} does not authorize {claim_kind}. "
            "Describe the observed boundary without claiming that the Skill "
            "caused the outcome."
        )
    return {
        "allowed": allowed,
        "causal_scope": causal_scope,
        "claim_kind": claim_kind,
        "reason": reason,
    }


def _finding_id(skill_run_id: str, code: str, stage: str) -> str:
    value = "\0".join((skill_run_id, code, stage))
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:20]
    return f"finding_{digest}"


def _unique(values: Iterable[str], limit: int = 4) -> List[str]:
    result: List[str] = []
    for value in values:
        if value and value not in result:
            result.append(value)
        if len(result) >= limit:
            break
    return result


def _weakest_event_grade(events: Iterable[Dict[str, Any]]) -> Optional[str]:
    order = {"observed": 0, "derived": 1, "inferred": 2, "experimental": 3}
    grades = [
        event.get("evidence_grade")
        for event in events
        if event.get("evidence_grade") in order
    ]
    return max(grades, key=order.get) if grades else None


def _finding(
    run: Dict[str, Any],
    *,
    code: str,
    title: str,
    summary: str,
    severity: str,
    stage: str,
    evidence_grade: str,
    causal_scope: str = "none",
    confidence: float,
    basis: Iterable[str],
    missing_signals: Iterable[str] = (),
    recommended_actions: Iterable[str] = (),
) -> Dict[str, Any]:
    return {
        "finding_id": _finding_id(run.get("skill_run_id", "unknown"), code, stage),
        "code": code,
        "title": title,
        "summary": summary,
        "severity": severity,
        "stage": stage,
        "evidence_grade": evidence_grade,
        "causal_scope": causal_scope,
        "confidence": confidence,
        "basis": _unique(basis),
        "missing_signals": _unique(missing_signals),
        "recommended_actions": _unique(recommended_actions),
    }


def _earliest_stage(events: Iterable[Dict[str, Any]]) -> Optional[str]:
    stages = {
        event.get("stage")
        for event in events
        if event.get("stage") in STAGE_INDEX
    }
    return min(stages, key=STAGE_INDEX.__getitem__) if stages else None


def diagnose_skill_run(run: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return deterministic, evidence-graded findings for one SkillRun."""
    events = list(run.get("events") or [])
    stage_summary = list(run.get("stage_summary") or [])
    findings: List[Dict[str, Any]] = []

    failed_events = [event for event in events if event.get("status") == "failed"]
    failed_stage = _earliest_stage(failed_events)
    if failed_stage:
        stage_events = [
            event for event in failed_events if event.get("stage") == failed_stage
        ]
        observed = any(
            event.get("evidence_grade") == "observed" for event in stage_events
        )
        findings.append(
            _finding(
                run,
                code="runtime_failure",
                title=f"{failed_stage.title()} reported a failure",
                summary=(
                    "The runtime source contains an explicit failure at the earliest "
                    f"observable failed lifecycle stage: {failed_stage}."
                ),
                severity="error",
                stage=failed_stage,
                evidence_grade="observed" if observed else "derived",
                confidence=1.0,
                basis=(
                    event.get("summary") or event.get("basis") or event.get("event_type", "")
                    for event in stage_events
                ),
                recommended_actions=(
                    "Inspect the failed event and its source locator.",
                    "Check parent events before changing the Skill instructions.",
                ),
            )
        )

    incomplete = (
        run.get("status") in {"incomplete", "interrupted"}
        or run.get("session_completeness") in {"incomplete", "partial"}
    )
    if incomplete:
        findings.append(
            _finding(
                run,
                code="run_incomplete",
                title="The SkillRun did not reach a complete recorded outcome",
                summary=(
                    "The source ended, was interrupted, or is partial. Later lifecycle "
                    "evidence may be missing, so this run should not be treated as a "
                    "complete success or failure."
                ),
                severity="warning",
                stage="outcome",
                evidence_grade="observed",
                confidence=1.0,
                basis=(
                    f"SkillRun status: {run.get('status', 'unknown')}",
                    f"Session completeness: {run.get('session_completeness', 'unknown')}",
                ),
                missing_signals=("outcome completion event",),
                recommended_actions=(
                    "Re-index the source after the agent session finishes.",
                    "Inspect whether the source transcript was truncated.",
                ),
            )
        )

    first_gap_index: Optional[int] = None
    later_observed: List[str] = []
    for index, stage in enumerate(stage_summary):
        if stage.get("status") != "not_observed":
            continue
        observed_after = [
            later.get("stage", "")
            for later in stage_summary[index + 1 :]
            if later.get("status") in {"observed", "failed"}
        ]
        if observed_after:
            first_gap_index = index
            later_observed = observed_after
            break

    if first_gap_index is not None:
        gap = stage_summary[first_gap_index]
        stage = gap.get("stage", "unknown")
        findings.append(
            _finding(
                run,
                code="lifecycle_evidence_gap",
                title=f"{stage.title()} evidence is missing before later activity",
                summary=(
                    f"No {stage} event was observed even though later lifecycle "
                    "activity exists. This is an evidence gap, not proof that the "
                    f"{stage} step did not occur."
                ),
                severity="warning",
                stage=stage,
                evidence_grade="derived",
                confidence=1.0,
                basis=(
                    f"Adapter capability for {stage}: {gap.get('capability', 'unknown')}",
                    "Later observed stages: " + ", ".join(later_observed),
                ),
                missing_signals=(f"{stage} lifecycle event",),
                recommended_actions=(
                    "Inspect the adapter capability and source telemetry settings.",
                    "Prefer a native lifecycle event or fail-open hook when available.",
                ),
            )
        )

    outcome_events = [event for event in events if event.get("stage") == "outcome"]
    if (
        outcome_events
        and not incomplete
        and (run.get("behavior_assessment") or {}).get("verifier_expected")
        and not any(
            event.get("event_type") == "outcome.verified" for event in outcome_events
        )
    ):
        findings.append(
            _finding(
                run,
                code="outcome_unverified",
                title="The outcome is reported but not independently verified",
                summary=(
                    "The run contains an agent or source-reported outcome, but no "
                    "deterministic test or explicit evaluation verifies its quality."
                ),
                severity="info",
                stage="outcome",
                evidence_grade="derived",
                confidence=1.0,
                basis=(
                    event.get("summary") or event.get("event_type", "")
                    for event in outcome_events
                ),
                missing_signals=("outcome.verified",),
                recommended_actions=(
                    "Attach a deterministic test or explicit evaluation when outcome "
                    "quality matters.",
                ),
            )
        )

    severity_rank = {"error": 0, "warning": 1, "info": 2}
    return sorted(
        findings,
        key=lambda finding: (
            STAGE_INDEX.get(finding["stage"], 99),
            severity_rank.get(finding["severity"], 9),
            finding["code"],
        ),
    )


def assess_skill_run(
    run: Dict[str, Any],
    findings: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Build an evidence-bounded assessment without claiming Skill causality.

    The checks describe whether the lifecycle evidence needed to inspect a run
    is present. They are not a Skill-specific behavioral contract and do not
    turn evidence coverage into a success score.
    """
    resolved_findings = findings if findings is not None else diagnose_skill_run(run)
    stages = {
        item.get("stage"): item
        for item in (run.get("stage_summary") or [])
        if item.get("stage")
    }
    events = list(run.get("events") or [])

    def stage_events(stage: str) -> List[Dict[str, Any]]:
        return [event for event in events if event.get("stage") == stage]

    def stage_check(
        stage: str,
        label: str,
        expected: str,
        observed: str,
        *,
        status: Optional[str] = None,
        basis: Iterable[str] = (),
    ) -> Dict[str, Any]:
        summary = stages.get(stage, {})
        resolved_status = status
        if resolved_status is None:
            if summary.get("status") == "failed":
                resolved_status = "deviation"
            elif summary.get("event_count"):
                resolved_status = "matched"
            elif summary.get("status") == "unsupported":
                resolved_status = "unobservable"
            else:
                resolved_status = "unconfirmed"
        return {
            "stage": stage,
            "label": label,
            "expected": expected,
            "observed": observed,
            "status": resolved_status,
            "evidence_grade": summary.get("evidence_grade"),
            "event_count": int(summary.get("event_count") or 0),
            "basis": _unique(basis),
        }

    activation = stages.get("activation", {})
    activation_events = stage_events("activation")
    activation_mode = run.get("activation_mode") or "unknown"
    if activation.get("event_count"):
        activation_observed = (
            f"{activation['event_count']} activation event(s) were observed; "
            f"mode: {activation_mode}."
        )
    elif activation.get("status") == "unsupported":
        activation_observed = (
            "The adapter does not expose activation lifecycle events."
        )
    else:
        activation_observed = (
            f"No activation event matched; mode remains {activation_mode}."
        )

    instructions = stages.get("instructions", {})
    instruction_observed = (
        f"{instructions.get('event_count', 0)} instruction load event(s) were observed."
        if instructions.get("event_count")
        else "No instruction load event was observed."
    )

    resources = stages.get("resources", {})
    resource_observed = (
        f"{resources.get('event_count', 0)} resource access event(s) were observed."
        if resources.get("event_count")
        else "No resource access event was observed."
    )

    execution = stages.get("execution", {})
    execution_observed = (
        f"{execution.get('event_count', 0)} execution event(s) were linked to "
        "this SkillRun; linkage describes scope, not causal effect."
        if execution.get("event_count")
        else "No execution event was linked to this SkillRun."
    )

    artifacts = stages.get("artifacts", {})
    artifact_observed = (
        f"{artifacts.get('event_count', 0)} artifact event(s) were connected "
        "to this SkillRun; artifact quality was not inferred."
        if artifacts.get("event_count")
        else "No artifact event was connected to this SkillRun."
    )

    outcome = stages.get("outcome", {})
    outcome_events = stage_events("outcome")
    verified_outcomes = [
        event for event in outcome_events
        if event.get("event_type") == "outcome.verified"
    ]
    source_incomplete = (
        run.get("status") in {"incomplete", "interrupted"}
        or run.get("session_completeness") in {"incomplete", "partial"}
    )
    if verified_outcomes:
        outcome_status = "matched"
        outcome_observed = (
            f"{len(verified_outcomes)} independently verified outcome event(s) "
            "were observed."
        )
    elif outcome_events:
        outcome_status = "unconfirmed"
        qualifier = (
            "The source session is incomplete."
            if source_incomplete
            else "No deterministic verification was observed."
        )
        outcome_observed = (
            f"{len(outcome_events)} outcome event(s) were reported. {qualifier}"
        )
    elif outcome.get("status") == "unsupported":
        outcome_status = "unobservable"
        outcome_observed = "The adapter does not expose outcome evidence."
    else:
        outcome_status = "unconfirmed"
        outcome_observed = "No outcome event was observed."

    checks = [
        stage_check(
            "activation",
            "Activation identity",
            "A direct signal identifies how the Skill entered active scope.",
            activation_observed,
            basis=(
                f"Activation mode: {activation_mode}",
                f"Adapter capability: {activation.get('capability', 'unsupported')}",
                *(event.get("basis", "") for event in activation_events),
            ),
        ),
        stage_check(
            "instructions",
            "Primary instructions",
            "The Skill's primary instructions are available to the run.",
            instruction_observed,
            basis=(event.get("basis", "") for event in stage_events("instructions")),
        ),
        stage_check(
            "resources",
            "Skill resources",
            "When a Skill resource is used, its access is visible.",
            resource_observed,
            basis=(event.get("basis", "") for event in stage_events("resources")),
        ),
        stage_check(
            "execution",
            "Runtime execution",
            "Runtime actions can be associated with the active SkillRun scope.",
            execution_observed,
            basis=(event.get("basis", "") for event in stage_events("execution")),
        ),
        stage_check(
            "artifacts",
            "Artifacts",
            "Created or modified artifacts can be connected to the run.",
            artifact_observed,
            basis=(event.get("basis", "") for event in stage_events("artifacts")),
        ),
        stage_check(
            "outcome",
            "Outcome verification",
            "A terminal result is independently verified when correctness matters.",
            outcome_observed,
            status=outcome_status,
            basis=(event.get("basis", "") for event in outcome_events),
        ),
    ]

    has_failure = any(
        finding.get("code") == "runtime_failure"
        for finding in resolved_findings
    )
    activity_entries = {
        entry.get("stage"): entry
        for entry in (run.get("activity_summary", {}).get("entries") or [])
    }
    execution_entry = activity_entries.get("execution", {})
    artifact_entry = activity_entries.get("artifacts", {})
    outcome_entry = activity_entries.get("outcome", {})
    tool_calls = sum(
        int(item.get("call_count") or 0)
        for item in (execution_entry.get("objects") or [])
    )
    logical_artifacts = len(artifact_entry.get("objects") or [])
    final_responses = sum(
        int(item.get("count") or 0)
        for item in (outcome_entry.get("objects") or [])
        if item.get("label") == "Final response"
    )
    reconstructable_stages = sum(
        bool(stages.get(stage, {}).get("event_count"))
        for stage in ("instructions", "resources", "execution", "artifacts", "outcome")
    )

    if reconstructable_stages >= 3:
        reconstruction_status = (
            "partial_source" if source_incomplete else "core_reconstructed"
        )
        reconstruction_title = (
            "Core activity reconstructed from a partial source"
            if source_incomplete
            else "Core activity reconstructed"
        )
        reconstruction_summary = (
            f"{tool_calls} tool call(s), {logical_artifacts} logical artifact(s), "
            f"and {final_responses} final response(s) are linked to this run."
        )
    elif reconstructable_stages:
        reconstruction_status = "partial"
        reconstruction_title = "Only part of the run can be reconstructed"
        reconstruction_summary = (
            f"{reconstructable_stages} of 5 inspectable activity stages contain "
            "records."
        )
    else:
        reconstruction_status = "unavailable"
        reconstruction_title = "Run activity cannot be reconstructed"
        reconstruction_summary = "No inspectable activity records are available."

    if has_failure:
        failure_status = "failure_observed"
        failure_title = "Explicit runtime failure observed"
        failure_summary = (
            "A source record explicitly reports failure. Inspect the earliest "
            "failed event; this does not establish that the Skill caused it."
        )
    elif events:
        failure_status = "no_failure_observed"
        failure_title = "No explicit runtime failure observed"
        failure_summary = (
            "The available records contain no explicit failed event. This is not "
            "proof that the result is correct."
        )
    else:
        failure_status = "unconfirmed"
        failure_title = "Runtime failure state is unconfirmed"
        failure_summary = "There are no runtime records to inspect for failures."

    if activation.get("event_count"):
        activation_status = "confirmed"
        activation_title = f"Enablement confirmed · {activation_mode}"
        activation_summary = (
            "A direct activation record identifies how the Skill entered active "
            "scope for this run."
        )
    elif activation.get("status") == "unsupported":
        activation_status = "unobservable"
        activation_title = "Enablement method is not exposed"
        activation_summary = (
            "This adapter does not provide the signal needed to identify whether "
            "the Skill was explicitly invoked, auto-selected, or always enabled."
        )
    else:
        activation_status = "unconfirmed"
        activation_title = "Enablement method is unconfirmed"
        activation_summary = (
            "Later instruction and execution evidence exists, but no direct signal "
            "shows how the Skill entered active scope."
        )

    if verified_outcomes:
        verification_status = "verified"
        verification_title = "Result independently verified"
        verification_summary = (
            f"{len(verified_outcomes)} deterministic verification event(s) support "
            "the reported result."
        )
    elif outcome_events:
        verification_status = "reported_not_verified"
        verification_title = "Final response reported; correctness unverified"
        verification_summary = (
            "The Agent's final response is available, but no deterministic test or "
            "explicit evaluation independently verifies its claims."
        )
    else:
        verification_status = "not_observed"
        verification_title = "No final result was observed"
        verification_summary = "The source contains no inspectable final response."

    dimensions = [
        {
            "dimension": "reconstruction",
            "label": "Run reconstruction",
            "status": reconstruction_status,
            "title": reconstruction_title,
            "summary": reconstruction_summary,
            "evidence_grade": "derived",
            "stage": "execution",
        },
        {
            "dimension": "runtime_failure",
            "label": "Observable failures",
            "status": failure_status,
            "title": failure_title,
            "summary": failure_summary,
            "evidence_grade": "derived",
            "stage": next(
                (
                    finding.get("stage")
                    for finding in resolved_findings
                    if finding.get("code") == "runtime_failure"
                ),
                "execution",
            ),
        },
        {
            "dimension": "activation",
            "label": "Skill enablement",
            "status": activation_status,
            "title": activation_title,
            "summary": activation_summary,
            "evidence_grade": (
                activation.get("evidence_grade")
                if activation.get("event_count")
                else "derived"
            ),
            "stage": "activation",
        },
        {
            "dimension": "outcome_verification",
            "label": "Result verification",
            "status": verification_status,
            "title": verification_title,
            "summary": verification_summary,
            "evidence_grade": "derived",
            "stage": "outcome",
        },
    ]

    reported_outcomes = [
        event
        for event in outcome_events
        if event.get("event_type") == "outcome.reported"
    ]
    failed_event_count = sum(
        event.get("status") == "failed" for event in events
    )
    behavior = run.get("behavior_assessment") or {
        "status": "definition_unavailable",
        "counts": {
            "total": 0,
            "checked": 0,
            "satisfied": 0,
            "deviations": 0,
            "expected_not_observed": 0,
            "not_evaluable": 0,
        },
        "constraints": [],
        "verifier_expected": False,
        "first_deviation_stage": None,
    }
    confirmed_failures = [
        {
            "code": finding.get("code"),
            "category": "runtime_failure",
            "severity": "error",
            "stage": finding.get("stage"),
            "title": finding.get("title"),
            "summary": finding.get("summary"),
            "evidence_grade": finding.get("evidence_grade"),
            "finding_id": finding.get("finding_id"),
        }
        for finding in resolved_findings
        if finding.get("code") == "runtime_failure"
    ]

    attention_items = list(confirmed_failures)
    behavior_issues = [
        item
        for item in (behavior.get("constraints") or [])
        if item.get("status") in {"deviation", "expected_not_observed"}
    ]
    for item in behavior_issues:
        attention_items.append(
            {
                "code": "skill_behavior_deviation",
                "category": "behavior_deviation",
                "severity": (
                    "error" if item.get("status") == "deviation" else "warning"
                ),
                "stage": item.get("stage"),
                "title": (
                    "A prohibited Skill behavior was observed"
                    if item.get("status") == "deviation"
                    else "An expected Skill behavior was not observed"
                ),
                "summary": (
                    f"Constraint target: {item.get('target_label')}. "
                    f"{item.get('basis')}"
                ),
                "impact": "Inspect the linked lifecycle boundary and source constraint.",
                "evidence_grade": item.get("evidence_grade") or "derived",
                "constraint_id": item.get("constraint_id"),
                "constraint_status": item.get("status"),
                "target_label": item.get("target_label"),
            }
        )
    if (
        reported_outcomes
        and not verified_outcomes
        and behavior.get("verifier_expected")
    ):
        attention_items.append(
            {
                "code": "result_not_verified",
                "category": "verification_gap",
                "severity": "warning",
                "stage": "outcome",
                "title": "Reported result is not independently verified",
                "summary": (
                    "The Agent's final response can be inspected, but no "
                    "deterministic test or explicit evaluation verifies its claims."
                ),
                "impact": (
                    "The execution record can be diagnosed, but result correctness "
                    "cannot be concluded from this run."
                ),
                "evidence_grade": "derived",
            }
        )
    elif not outcome_events:
        attention_items.append(
            {
                "code": "result_not_observed",
                "category": "result_gap",
                "severity": "warning",
                "stage": "outcome",
                "title": "No final result was observed",
                "summary": "The source contains no inspectable final response.",
                "impact": "Completion and result quality cannot be assessed.",
                "evidence_grade": "derived",
            }
        )

    observability_limits: List[Dict[str, Any]] = []
    if source_incomplete:
        observability_limits.append(
            {
                "code": "source_incomplete",
                "category": "observability",
                "stage": "outcome",
                "title": "The source may be incomplete",
                "summary": (
                    "Core activity is present, but the source is marked partial or "
                    "incomplete, so later or intermediate events may be missing."
                ),
                "impact": "Absence of an event cannot be treated as proof it did not occur.",
                "evidence_grade": "observed",
            }
        )
    if activation_status in {"unconfirmed", "unobservable"}:
        observability_limits.append(
            {
                "code": "enablement_unconfirmed",
                "category": "observability",
                "stage": "activation",
                "title": "Skill enablement method is unconfirmed",
                "summary": (
                    "Later Skill activity is visible, but no direct signal identifies "
                    "how this Skill became active for the request."
                    if activation_status == "unconfirmed"
                    else "The adapter does not expose Skill activation lifecycle events."
                ),
                "impact": (
                    "Explicit invocation, automatic selection, and always-on "
                    "enablement cannot be distinguished."
                ),
                "evidence_grade": "derived",
            }
        )

    confirmed_facts: List[Dict[str, Any]] = []
    if instructions.get("event_count"):
        confirmed_facts.append(
            {
                "code": "instructions_loaded",
                "stage": "instructions",
                "title": "Primary instructions loaded",
                "summary": (
                    f"{instructions.get('event_count', 0)} instruction source(s) "
                    "were observed."
                ),
                "evidence_grade": instructions.get("evidence_grade") or "observed",
            }
        )
    if resources.get("event_count"):
        confirmed_facts.append(
            {
                "code": "resources_accessed",
                "stage": "resources",
                "title": "Skill resources accessed",
                "summary": (
                    f"{resources.get('event_count', 0)} resource access record(s) "
                    "were observed."
                ),
                "evidence_grade": resources.get("evidence_grade") or "observed",
            }
        )
    if execution.get("event_count"):
        confirmed_facts.append(
            {
                "code": "tool_calls_recorded",
                "stage": "execution",
                "title": "Tool execution recorded",
                "summary": (
                    f"{tool_calls} tool call(s) were paired from "
                    f"{execution.get('event_count', 0)} lifecycle record(s)."
                ),
                "evidence_grade": "derived",
            }
        )
    if artifacts.get("event_count"):
        confirmed_facts.append(
            {
                "code": "artifacts_recorded",
                "stage": "artifacts",
                "title": "Artifacts recorded",
                "summary": (
                    f"{logical_artifacts} logical artifact(s) were grouped from "
                    f"{artifacts.get('event_count', 0)} file record(s)."
                ),
                "evidence_grade": "derived",
            }
        )
    if reported_outcomes:
        confirmed_facts.append(
            {
                "code": "final_response_available",
                "stage": "outcome",
                "title": "Final response available",
                "summary": (
                    f"{final_responses or 1} final response(s) can be inspected."
                ),
                "evidence_grade": _weakest_event_grade(reported_outcomes),
            }
        )

    reasoning_steps: List[Dict[str, Any]] = []
    if execution.get("event_count"):
        reasoning_steps.append(
            {
                "code": "pair_tool_calls",
                "summary": (
                    f"{execution.get('event_count', 0)} tool lifecycle record(s) "
                    f"were paired by source call ID into {tool_calls} call(s)."
                ),
            }
        )
    if artifacts.get("event_count"):
        reasoning_steps.append(
            {
                "code": "group_artifacts",
                "summary": (
                    f"{artifacts.get('event_count', 0)} file record(s) were grouped "
                    f"by canonical path into {logical_artifacts} logical artifact(s)."
                ),
            }
        )
    reasoning_steps.append(
        {
            "code": "scan_failures",
            "summary": (
                f"{failed_event_count} source event(s) explicitly report failed status."
            ),
        }
    )
    reasoning_steps.append(
        {
            "code": "separate_report_from_verification",
            "summary": (
                f"{len(reported_outcomes)} reported outcome event(s) and "
                f"{len(verified_outcomes)} independent verification event(s) "
                "were kept separate."
            ),
        }
    )

    verification_gap_count = sum(
        item.get("category") == "verification_gap"
        for item in attention_items
    )
    behavior_deviation_count = len(behavior_issues)
    if confirmed_failures:
        diagnosis_status = "explicit_failure"
        diagnosis_title = "An explicit runtime failure was observed"
        diagnosis_summary = (
            "Inspect the earliest failed lifecycle boundary. The record does not "
            "establish that the Skill caused the failure."
        )
    elif behavior_deviation_count:
        diagnosis_status = "behavior_deviation"
        diagnosis_title = (
            f"{behavior_deviation_count} expected Skill behavior(s) need review"
        )
        diagnosis_summary = (
            "The current Skill definition contains checkable behavior constraints; "
            "one or more do not match the observable runtime evidence."
        )
    elif verification_gap_count:
        diagnosis_status = "result_unverified"
        diagnosis_title = (
            "No explicit execution failure was observed; result correctness is "
            "unverified"
        )
        diagnosis_summary = (
            "Instructions, runtime activity, artifacts, and a final response are "
            "available for inspection. No deterministic verifier confirms the "
            "Agent's completion claims."
        )
    elif verified_outcomes:
        diagnosis_status = "result_verified"
        diagnosis_title = "No explicit execution failure was observed; result verified"
        diagnosis_summary = (
            "The runtime record contains an independent verification signal. This "
            "still does not establish that the Skill caused the outcome."
        )
    elif reported_outcomes:
        diagnosis_status = "no_observed_issue"
        diagnosis_title = "No observable runtime issue was found"
        diagnosis_summary = (
            "The available evidence shows Skill activity and a final response. "
            "Outcome verification is not configured for this run and is not "
            "counted as a failure."
        )
    else:
        diagnosis_status = "result_not_observed"
        diagnosis_title = "No explicit execution failure was observed; no result is available"
        diagnosis_summary = (
            "The available runtime record contains no explicit failed event, but "
            "there is no final result to inspect."
        )

    diagnosis = {
        "status": diagnosis_status,
        "title": diagnosis_title,
        "summary": diagnosis_summary,
        "counts": {
            "confirmed_failures": len(confirmed_failures),
            "behavior_deviations": behavior_deviation_count,
            "verification_gaps": verification_gap_count,
            "observability_limits": len(observability_limits),
        },
        "attention_items": attention_items,
        "confirmed_facts": confirmed_facts,
        "observability_limits": observability_limits,
        "conformance": behavior,
        "reasoning": {
            "method": "deterministic_rules",
            "label": "Calculated by system rules",
            "summary": (
                "Fixed rules pair and group normalized source records. The same "
                "evidence produces the same summary; no model-generated explanation "
                "is used for this judgment."
            ),
            "steps": reasoning_steps,
            "evidence_grade": "derived",
            "causal_scope": "none",
            "does_not_establish": [
                "that the Skill caused the final outcome",
                "that the reported result is correct",
                "that an unobserved event did not occur",
            ],
        },
    }
    open_questions = [
        dimension
        for dimension in dimensions
        if dimension["status"]
        in {
            "partial",
            "partial_source",
            "unavailable",
            "unconfirmed",
            "unobservable",
            "reported_not_verified",
            "not_observed",
        }
    ]
    if has_failure:
        verdict = "observable_failure"
        title = "An explicit runtime failure was observed"
        summary = (
            "Inspect the earliest failed event. This describes the recorded "
            "runtime failure; it does not establish that the Skill caused it."
        )
    elif open_questions:
        verdict = "open_questions"
        title = (
            f"Core activity reconstructed · {len(open_questions)} open "
            f"question{'s' if len(open_questions) != 1 else ''}"
            if reconstruction_status in {"core_reconstructed", "partial_source"}
            else f"{len(open_questions)} open questions remain"
        )
        summary = (
            "Known activity and unresolved questions are shown separately. "
            "A missing enablement signal or independent verification does not erase "
            "the runtime evidence that was observed."
        )
    else:
        verdict = "no_observed_deviation"
        title = "No observable deviation was found"
        summary = (
            "Available lifecycle checks are supported by evidence. This is not "
            "proof that the Skill caused the outcome or that the result is correct."
        )

    return {
        "verdict": verdict,
        "title": title,
        "summary": summary,
        "evidence_grade": "derived",
        "causal_scope": "none",
        "open_question_count": len(open_questions),
        "diagnosis": diagnosis,
        "dimensions": dimensions,
        "checks": checks,
        "discipline": (
            "Expected evidence means the signal needed to inspect the run; it is "
            "not a claim that every Skill must perform every stage. Attribution "
            "links an event to run scope and does not establish causality."
        ),
    }
