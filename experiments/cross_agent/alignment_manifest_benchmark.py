#!/usr/bin/env python3
"""Audit field-level comparability decisions for cross-Agent manifests."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


CLOCK_TOLERANCE_SECONDS = 5


def _run(
    agent: str,
    *,
    task_digest: str = "task-a",
    skill_digest: str = "skill-a",
    started_offset_seconds: int = 0,
    terminal_observed: bool = True,
    outcome_supported: bool = True,
    outcome_status: str = "completed",
    outcome_verified: bool = False,
) -> Dict[str, Any]:
    return {
        "agent": agent,
        "alignment_key": "case-a",
        "task_digest": task_digest,
        "skill_digest": skill_digest,
        "entrypoint": "explicit-skill",
        "started_offset_seconds": started_offset_seconds,
        "terminal_observed": terminal_observed,
        "capabilities": {
            "lifecycle": True,
            "outcome": outcome_supported,
        },
        "outcome_status": outcome_status,
        "outcome_verified": outcome_verified,
    }


def _cases() -> List[Dict[str, Any]]:
    return [
        {
            "name": "equivalent",
            "runs": [_run("qoder"), _run("opencode", started_offset_seconds=2)],
            "expected_decision": "comparable",
            "expected_dimensions": [
                "absolute_time",
                "lifecycle",
                "outcome",
            ],
            "expected_flags": [],
        },
        {
            "name": "clock-skew",
            "runs": [_run("qoder"), _run("opencode", started_offset_seconds=90)],
            "expected_decision": "comparable",
            "expected_dimensions": ["lifecycle", "outcome"],
            "expected_flags": ["clock_skew"],
        },
        {
            "name": "task-mismatch",
            "runs": [_run("qoder"), _run("opencode", task_digest="task-b")],
            "expected_decision": "not_comparable",
            "expected_dimensions": [],
            "expected_flags": ["task_mismatch"],
        },
        {
            "name": "missing-terminal",
            "runs": [_run("qoder"), _run("opencode", terminal_observed=False)],
            "expected_decision": "partially_comparable",
            "expected_dimensions": ["absolute_time", "lifecycle"],
            "expected_flags": ["terminal_missing"],
        },
        {
            "name": "reported-outcome-conflict",
            "runs": [
                _run("qoder", outcome_status="completed"),
                _run("opencode", outcome_status="failed"),
            ],
            "expected_decision": "comparable",
            "expected_dimensions": [
                "absolute_time",
                "lifecycle",
                "outcome",
            ],
            "expected_flags": ["reported_outcome_conflict"],
        },
        {
            "name": "verified-outcome-difference",
            "runs": [
                _run(
                    "qoder",
                    outcome_status="completed",
                    outcome_verified=True,
                ),
                _run(
                    "opencode",
                    outcome_status="failed",
                    outcome_verified=True,
                ),
            ],
            "expected_decision": "comparable",
            "expected_dimensions": [
                "absolute_time",
                "lifecycle",
                "outcome",
            ],
            "expected_flags": ["verified_outcome_difference"],
        },
        {
            "name": "outcome-capability-mask",
            "runs": [_run("qoder"), _run("opencode", outcome_supported=False)],
            "expected_decision": "partially_comparable",
            "expected_dimensions": ["absolute_time", "lifecycle"],
            "expected_flags": ["outcome_capability_masked"],
        },
        {
            "name": "skill-version-mismatch-uncontrolled",
            "runs": [_run("qoder"), _run("opencode", skill_digest="skill-b")],
            "expected_decision": "not_comparable",
            "expected_dimensions": [],
            "expected_flags": ["skill_digest_mismatch"],
        },
        {
            "name": "skill-version-comparison",
            "comparison_axis": "skill_version",
            "runs": [_run("qoder"), _run("opencode", skill_digest="skill-b")],
            "expected_decision": "comparable",
            "expected_dimensions": [
                "absolute_time",
                "lifecycle",
                "outcome",
            ],
            "expected_flags": ["skill_version_comparison"],
        },
    ]


def evaluate_alignment(
    case: Dict[str, Any],
    *,
    clock_tolerance_seconds: int = CLOCK_TOLERANCE_SECONDS,
) -> Dict[str, Any]:
    runs = list(case.get("runs") or [])
    flags = []
    dimensions = []
    if len(runs) < 2:
        return {
            "decision": "not_comparable",
            "dimensions": [],
            "flags": ["insufficient_runs"],
            "causal_attribution_allowed": False,
        }

    alignment_keys = {run.get("alignment_key") for run in runs}
    task_digests = {run.get("task_digest") for run in runs}
    entrypoints = {run.get("entrypoint") for run in runs}
    skill_digests = {run.get("skill_digest") for run in runs}
    if len(alignment_keys) != 1 or None in alignment_keys:
        flags.append("alignment_key_mismatch")
    if len(task_digests) != 1 or None in task_digests:
        flags.append("task_mismatch")
    if len(entrypoints) != 1 or None in entrypoints:
        flags.append("entrypoint_mismatch")
    if len(skill_digests) != 1:
        if case.get("comparison_axis") == "skill_version":
            flags.append("skill_version_comparison")
        else:
            flags.append("skill_digest_mismatch")

    blocking = {
        "alignment_key_mismatch",
        "task_mismatch",
        "entrypoint_mismatch",
        "skill_digest_mismatch",
    }
    if blocking & set(flags):
        return {
            "decision": "not_comparable",
            "dimensions": [],
            "flags": sorted(flags),
            "causal_attribution_allowed": False,
        }

    if all(run.get("capabilities", {}).get("lifecycle") for run in runs):
        dimensions.append("lifecycle")
    else:
        flags.append("lifecycle_capability_masked")

    terminal_observed = all(run.get("terminal_observed") for run in runs)
    outcome_supported = all(
        run.get("capabilities", {}).get("outcome") for run in runs
    )
    if not terminal_observed:
        flags.append("terminal_missing")
    if not outcome_supported:
        flags.append("outcome_capability_masked")
    if terminal_observed and outcome_supported:
        dimensions.append("outcome")
        statuses = {run.get("outcome_status") for run in runs}
        if len(statuses) > 1:
            if all(run.get("outcome_verified") for run in runs):
                flags.append("verified_outcome_difference")
            else:
                flags.append("reported_outcome_conflict")

    offsets = [int(run.get("started_offset_seconds") or 0) for run in runs]
    if max(offsets) - min(offsets) <= clock_tolerance_seconds:
        dimensions.append("absolute_time")
    else:
        flags.append("clock_skew")

    decision = (
        "comparable"
        if {"lifecycle", "outcome"}.issubset(dimensions)
        else "partially_comparable"
        if dimensions
        else "not_comparable"
    )
    return {
        "decision": decision,
        "dimensions": sorted(dimensions),
        "flags": sorted(flags),
        "causal_attribution_allowed": False,
    }


def run_experiment() -> Dict[str, Any]:
    cases = _cases()
    results = []
    for case in cases:
        actual = evaluate_alignment(case)
        exact = (
            actual["decision"] == case["expected_decision"]
            and actual["dimensions"]
            == sorted(case["expected_dimensions"])
            and actual["flags"] == sorted(case["expected_flags"])
            and not actual["causal_attribution_allowed"]
        )
        results.append(
            {
                "case": case["name"],
                "exact": exact,
                "decision": actual["decision"],
                "dimension_count": len(actual["dimensions"]),
                "flag_count": len(actual["flags"]),
                "causal_attribution_allowed": actual[
                    "causal_attribution_allowed"
                ],
            }
        )
    metrics = {
        "case_count": len(results),
        "exact_cases": sum(result["exact"] for result in results),
        "comparable_cases": sum(
            result["decision"] == "comparable" for result in results
        ),
        "partially_comparable_cases": sum(
            result["decision"] == "partially_comparable"
            for result in results
        ),
        "not_comparable_cases": sum(
            result["decision"] == "not_comparable" for result in results
        ),
        "unsupported_causal_attribution_cases": sum(
            result["causal_attribution_allowed"] for result in results
        ),
    }
    report = {
        "schema_version": "sri.experiment.alignment-manifest.v1",
        "experiment": {
            "name": "cross-agent-alignment-manifest-conflict-contract",
            "evidence_grade": "Experimental",
            "clock_tolerance_seconds": CLOCK_TOLERANCE_SECONDS,
            "synthetic_contract_cases": True,
            "limitations": [
                "Contract cases do not establish real Agent behavior or schema compatibility.",
                "The clock threshold is a test policy, not an estimated optimal value.",
                "Comparability permits evidence comparison, not causal attribution.",
                "Outcome verification quality is assumed by the fixture and not evaluated here.",
            ],
        },
        "metrics": metrics,
        "cases": results,
        "gate": {
            "name": "field-level alignment decisions exact",
            "passed": (
                metrics["exact_cases"] == metrics["case_count"]
                and metrics["unsupported_causal_attribution_cases"] == 0
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment()
    output = write_report(
        EXPERIMENT_DIR,
        "alignment-manifest",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
