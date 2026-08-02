#!/usr/bin/env python3
"""Audit whether repeated native launch data is ready for effect claims."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


EXPECTED_EXPERIMENT = "native-sender-placement-signature-factorial"


def _position_balance(report: Dict[str, Any]) -> bool:
    positions = {}
    for row in report.get("trials", []):
        key = (
            row["placement"],
            row["provenance"],
            row["signature"],
        )
        positions.setdefault(key, [0, 0, 0, 0])
        positions[key][row["position"]] += 1
    return bool(positions) and all(
        counts == [2, 2, 2, 2] for counts in positions.values()
    )


def audit_reports(
    reports: Sequence[Dict[str, Any]],
    summary: Dict[str, Any],
) -> Dict[str, Any]:
    if not reports:
        raise ValueError("at least one report is required")
    if any(
        report.get("experiment", {}).get("name") != EXPECTED_EXPERIMENT
        for report in reports
    ):
        raise ValueError("report experiment name mismatch")
    factor_boundaries = summary["metrics"]["factor_run_boundaries"]
    raw_trials = [
        row
        for report in reports
        for row in report.get("trials", [])
    ]
    cell_boundaries = summary["metrics"]["per_run_cell_boundaries"]
    cell_run_ratios = {
        key: (
            max(value["p50_values_ms"]) / min(value["p50_values_ms"])
        )
        for key, value in cell_boundaries.items()
    }
    direction_consistency = {
        factor: value["direction_consistent_across_run_p50s"]
        for factor, value in factor_boundaries.items()
    }
    host_contexts = {
        json.dumps(
            {
                "platform": report.get("environment", {}).get("platform"),
                "machine": report.get("environment", {}).get("machine"),
            },
            sort_keys=True,
        )
        for report in reports
    }
    host_ids = [
        report.get("environment", {}).get("host_id")
        for report in reports
    ]
    stable_host_identity_recorded = all(host_ids)
    independent_host_replication = (
        stable_host_identity_recorded and len(set(host_ids)) >= 2
    )
    steady_state_established = all(
        report.get("experiment", {}).get("steady_state_established") is True
        for report in reports
    )
    sample_size_justified = (
        summary.get("experiment", {}).get(
            "confirmatory_sample_size_justified"
        )
        is True
    )
    criteria = {
        "raw_trials_available": len(raw_trials) > 0,
        "all_integrity_gates_passed": all(
            report["gate"]["passed"] for report in reports
        ),
        "all_manipulation_checks_passed": all(
            row["factor_setup"]["passed"] for row in raw_trials
        ),
        "run_boundaries_preserved": len(reports) >= 2,
        "within_run_position_balanced": all(
            _position_balance(report) for report in reports
        ),
        "stable_host_identity_recorded": stable_host_identity_recorded,
        "independent_host_replication": independent_host_replication,
        "factor_direction_consistent_across_runs": all(
            direction_consistency.values()
        ),
        "steady_state_established": steady_state_established,
        "confirmatory_sample_size_justified": sample_size_justified,
    }
    descriptive_keys = (
        "raw_trials_available",
        "all_integrity_gates_passed",
        "all_manipulation_checks_passed",
        "run_boundaries_preserved",
        "within_run_position_balanced",
    )
    descriptive_ready = all(criteria[key] for key in descriptive_keys)
    confirmatory_ready = all(criteria.values())
    return {
        "schema_version": "sri.experiment.native-launch-phase-readiness.v1",
        "experiment": {
            "name": "native-launch-phase-aware-readiness-audit",
            "evidence_grade": "Derived",
            "method_status": "post_hoc_exploratory_audit",
            "limitations": [
                "No change point or steady state is inferred from the short interleaved sequence.",
                "The reports lack a stable privacy-safe host identifier.",
                "Three same-environment runs do not justify a confirmatory effect estimate.",
                "Readiness criteria describe evidence availability, not a latency mechanism.",
            ],
        },
        "metrics": {
            "report_count": len(reports),
            "raw_trial_count": len(raw_trials),
            "observed_host_context_count": len(host_contexts),
            "cell_run_p50_ratio": cell_run_ratios,
            "factor_direction_consistency": direction_consistency,
            "criteria_passed": sum(criteria.values()),
            "criteria_total": len(criteria),
        },
        "criteria": criteria,
        "readiness": {
            "descriptive_analysis_ready": descriptive_ready,
            "confirmatory_effect_ready": confirmatory_ready,
            "allowed_claim": (
                "phase-preserving descriptive association"
                if descriptive_ready
                else "integrity audit only"
            ),
            "prohibited_claims": [
                "steady-state latency effect",
                "signature causal effect",
                "cross-host generalization",
            ],
        },
        "gate": {
            "name": "phase-readiness audit integrity",
            "passed": (
                descriptive_ready
                and len(criteria) == 10
                and not confirmatory_ready
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in arguments.reports
    ]
    summary = json.loads(arguments.summary.read_text(encoding="utf-8"))
    report = audit_reports(reports, summary)
    output = write_report(
        EXPERIMENT_DIR,
        "native-launch-phase-readiness",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["readiness"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
