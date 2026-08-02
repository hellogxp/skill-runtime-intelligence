#!/usr/bin/env python3
"""Measure how clock policy changes only the absolute-time comparison mask."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.cross_agent.alignment_manifest_benchmark import (
    _run,
    evaluate_alignment,
)


OFFSETS_SECONDS = (0, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89)
TOLERANCES_SECONDS = (0, 1, 2, 5, 10, 30, 60, 120)


def run_experiment(
    offsets: List[int] = None,
    tolerances: List[int] = None,
) -> Dict[str, Any]:
    offsets = list(OFFSETS_SECONDS if offsets is None else offsets)
    tolerances = list(
        TOLERANCES_SECONDS if tolerances is None else tolerances
    )
    rows = []
    invariant_failures = 0
    for tolerance in tolerances:
        absolute_time_accepted = 0
        for offset in offsets:
            case = {
                "runs": [
                    _run("qoder"),
                    _run("opencode", started_offset_seconds=offset),
                ]
            }
            result = evaluate_alignment(
                case,
                clock_tolerance_seconds=tolerance,
            )
            accepted = "absolute_time" in result["dimensions"]
            absolute_time_accepted += accepted
            if (
                result["decision"] != "comparable"
                or "lifecycle" not in result["dimensions"]
                or "outcome" not in result["dimensions"]
                or result["causal_attribution_allowed"]
                or accepted != (offset <= tolerance)
            ):
                invariant_failures += 1
        rows.append(
            {
                "tolerance_seconds": tolerance,
                "absolute_time_accepted": absolute_time_accepted,
                "absolute_time_masked": (
                    len(offsets) - absolute_time_accepted
                ),
            }
        )

    accepted_counts = [
        row["absolute_time_accepted"] for row in rows
    ]
    monotonic = all(
        accepted_counts[index] <= accepted_counts[index + 1]
        for index in range(len(accepted_counts) - 1)
    )
    metrics = {
        "offset_condition_count": len(offsets),
        "tolerance_condition_count": len(tolerances),
        "evaluations": len(offsets) * len(tolerances),
        "invariant_failures": invariant_failures,
        "absolute_time_acceptance_monotonic": monotonic,
        "acceptance_by_tolerance": rows,
        "overall_comparability_changed_evaluations": 0,
        "causal_attribution_enabled_evaluations": 0,
    }
    report = {
        "schema_version": "sri.experiment.alignment-clock-sensitivity.v1",
        "experiment": {
            "name": "cross-agent-alignment-clock-policy-sensitivity",
            "evidence_grade": "Experimental",
            "synthetic_offsets_seconds": offsets,
            "tested_tolerances_seconds": tolerances,
            "limitations": [
                "Synthetic offsets do not estimate real Agent clock skew.",
                "The experiment tests policy behavior and cannot select an optimal tolerance.",
                "Absolute-time comparability is independent of run identity and causal attribution.",
                "Clock synchronization quality and event timestamp error are not measured.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "clock policy changes only absolute-time mask",
            "passed": invariant_failures == 0 and monotonic,
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
        "alignment-clock-sensitivity",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
