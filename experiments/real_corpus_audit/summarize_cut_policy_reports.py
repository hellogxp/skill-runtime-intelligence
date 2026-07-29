#!/usr/bin/env python3
"""Aggregate privacy-safe dataset cut-policy pilot reports."""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


def _summary(values: Iterable[float]) -> Dict[str, float]:
    values = list(values)
    return {
        "mean": statistics.fmean(values),
        "minimum": min(values),
        "maximum": max(values),
    }


def _aggregate(reports: list) -> Dict[str, Any]:
    policy_names = sorted(
        set.intersection(
            *[
                set(report["evaluation"]["policies"])
                for report in reports
            ]
        )
    )
    policies = {}
    for policy_name in policy_names:
        rows = [
            report["evaluation"]["policies"][policy_name]
            for report in reports
        ]
        selected = sum(int(row["selected_run_count"]) for row in rows)
        stable = sum(
            int(row["stable_next_interval_count"]) for row in rows
        )
        changed = sum(
            int(row["changed_next_interval_count"]) for row in rows
        )
        missing = sum(
            int(row["missing_next_interval_count"]) for row in rows
        )
        stability_values = [
            float(row["stable_next_interval_fraction"])
            for row in rows
            if row["stable_next_interval_fraction"] is not None
        ]
        policies[policy_name] = {
            "trial_count": len(rows),
            "pooled_selected_run_count": selected,
            "pooled_stable_next_interval_count": stable,
            "pooled_changed_next_interval_count": changed,
            "pooled_missing_next_interval_count": missing,
            "pooled_stable_next_interval_fraction": (
                stable / selected if selected else None
            ),
            "selection_fraction_across_trials": _summary(
                float(row["selection_fraction"]) for row in rows
            ),
            "stable_fraction_across_trials": (
                _summary(stability_values) if stability_values else None
            ),
        }
    return {
        "trial_count": len(reports),
        "policy_count": len(policy_names),
        "policies": policies,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in arguments.inputs
    ]
    source_gates_passed = all(
        report.get("gate", {}).get("passed")
        and report.get("privacy_audit", {}).get("passed")
        for report in reports
    )
    aggregate = _aggregate(reports)
    report = {
        "schema_version": "sri.experiment.dataset-cut-policy-summary.v1",
        "experiment": {
            "name": "privacy-safe-dataset-cut-policy-pilot-summary",
            "evidence_grade": "Experimental",
            "row_level_records_included": False,
            "limitations": [
                "Three trials from one local database are exploratory.",
                "Pooled run observations are not independent participants.",
                "No policy was randomized and no causal effect is estimated.",
                "Short-window stability does not prove source completeness.",
            ],
        },
        "aggregate": aggregate,
        "gate": {
            "name": "privacy-safe cut-policy reports aggregated",
            "passed": source_gates_passed and len(reports) >= 2,
        },
    }
    output = write_report(
        EXPERIMENT_DIR,
        "dataset-cut-policy-summary",
        report,
        arguments.output,
    )
    print(json.dumps({"aggregate": aggregate, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
