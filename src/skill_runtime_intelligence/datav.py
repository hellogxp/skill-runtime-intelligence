"""Privacy-minimized, read-only datasets for DataV dashboards.

The detailed SkillRun evidence remains in SRI.  These datasets intentionally
contain only categorical and aggregate fields that are useful for a customer
overview; they never include prompts, tool payloads, source paths, or raw
records.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from .storage import Storage


DATAV_DATASET_VERSION = "sri-datav-v1"
DATASET_PATHS = {
    "summary": "/api/datav/summary",
    "boundaries": "/api/datav/boundaries",
    "skills": "/api/datav/skills",
    "runs": "/api/datav/runs",
}


def _percentage(part: int, whole: int) -> float:
    if not whole:
        return 0.0
    return round(part * 100.0 / whole, 1)


def build_datav_datasets(storage: Storage, limit: int = 300) -> Dict[str, Any]:
    """Build flat, DataV-friendly datasets from normalized SkillRuns."""

    runs = storage.list_skill_runs(limit=max(1, min(int(limit), 1000)))
    total = len(runs)
    explicit_failures = sum(
        run.get("status") == "failed" or int(run.get("error_count") or 0) > 0
        for run in runs
    )
    boundary_runs = sum(bool(run.get("first_gap")) for run in runs)
    average_coverage = (
        round(
            sum(int(run.get("evidence_completeness") or 0) for run in runs)
            / total,
            1,
        )
        if total
        else 0.0
    )
    skill_names = {str(run.get("name") or "unknown") for run in runs}

    summary = [
        {
            "metric": "skill_runs",
            "label": "SkillRuns",
            "value": total,
            "unit": "runs",
            "evidence_grade": "derived",
            "interpretation": "Count of reconstructed SkillRuns in this dataset.",
        },
        {
            "metric": "skills_observed",
            "label": "Skills observed",
            "value": len(skill_names),
            "unit": "skills",
            "evidence_grade": "derived",
            "interpretation": "Distinct Skill identities represented by runtime evidence.",
        },
        {
            "metric": "explicit_failure_runs",
            "label": "Runs with explicit failure evidence",
            "value": explicit_failures,
            "unit": "runs",
            "evidence_grade": "derived",
            "interpretation": "A source event or run status explicitly reported failure.",
        },
        {
            "metric": "first_boundary_runs",
            "label": "Runs with a first observable boundary",
            "value": boundary_runs,
            "unit": "runs",
            "evidence_grade": "derived",
            "interpretation": (
                "A diagnostic starting point; missing evidence is not proof of failure."
            ),
        },
        {
            "metric": "average_evidence_coverage",
            "label": "Average evidence coverage",
            "value": average_coverage,
            "unit": "percent",
            "evidence_grade": "derived",
            "interpretation": "Observability coverage, not a quality or pass score.",
        },
    ]

    boundary_counts = Counter(
        str(run["first_gap"]) for run in runs if run.get("first_gap")
    )
    boundaries = [
        {
            "boundary": boundary,
            "run_count": count,
            "share_percent": _percentage(count, total),
            "evidence_grade": "derived",
            "meaning": "first_observable_boundary_not_causal_attribution",
        }
        for boundary, count in sorted(
            boundary_counts.items(), key=lambda item: (-item[1], item[0])
        )
    ]

    skill_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for run in runs:
        skill_groups[str(run.get("name") or "unknown")].append(run)
    skills = []
    for name, group in sorted(
        skill_groups.items(), key=lambda item: (-len(item[1]), item[0])
    ):
        failures = sum(
            run.get("status") == "failed" or int(run.get("error_count") or 0) > 0
            for run in group
        )
        gaps = sum(bool(run.get("first_gap")) for run in group)
        coverage = round(
            sum(int(run.get("evidence_completeness") or 0) for run in group)
            / len(group),
            1,
        )
        skills.append(
            {
                "skill_name": name,
                "run_count": len(group),
                "explicit_failure_count": failures,
                "first_boundary_count": gaps,
                "average_evidence_coverage": coverage,
                "evidence_grade": "derived",
            }
        )

    run_rows = [
        {
            "skill_run_id": str(run.get("skill_run_id") or ""),
            "started_at": run.get("started_at") or "",
            "skill_name": str(run.get("name") or "unknown"),
            "agent": str(run.get("adapter") or "unknown"),
            "status": str(run.get("status") or "unknown"),
            "evidence_coverage": int(run.get("evidence_completeness") or 0),
            "first_observable_boundary": run.get("first_gap") or "",
            "explicit_error_count": int(run.get("error_count") or 0),
            "detail_path": (
                f"#/runs/{run.get('skill_run_id')}"
                if run.get("skill_run_id")
                else "#/runs"
            ),
            "evidence_grade": "derived",
        }
        for run in runs
    ]

    return {
        "manifest": {
            "version": DATAV_DATASET_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "datasets": DATASET_PATHS,
            "record_limit": max(1, min(int(limit), 1000)),
            "privacy": {
                "raw_prompts": False,
                "tool_payloads": False,
                "source_paths": False,
                "credentials": False,
            },
            "discipline": (
                "All dashboard aggregates are Derived. Evidence coverage is not a "
                "pass score, and a first observable boundary is not a causal claim."
            ),
        },
        "summary": summary,
        "boundaries": boundaries,
        "skills": skills,
        "runs": run_rows,
    }
