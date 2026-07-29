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


def _finding(
    run: Dict[str, Any],
    *,
    code: str,
    title: str,
    summary: str,
    severity: str,
    stage: str,
    evidence_grade: str,
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
