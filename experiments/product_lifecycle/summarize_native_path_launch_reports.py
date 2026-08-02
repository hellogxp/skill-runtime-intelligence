#!/usr/bin/env python3
"""Aggregate repeated native path-launch reports without causal inference."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.product_lifecycle.native_sender_path_launch_benchmark import (
    CELLS,
    summarize,
)


def summarize_reports(reports: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not reports:
        raise ValueError("at least one report is required")
    expected_name = "native-sender-path-reuse-launch-sensitivity"
    if any(
        report.get("experiment", {}).get("name") != expected_name
        for report in reports
    ):
        raise ValueError("report experiment name mismatch")
    all_rows = [
        row
        for report in reports
        for row in report.get("trials", [])
    ]
    pooled = {}
    per_run = {}
    for artifact, condition in CELLS:
        key = f"{artifact}:{condition}"
        pooled[key] = summarize(
            [
                row["wall_ms"]
                for row in all_rows
                if row["artifact"] == artifact
                and row["condition"] == condition
            ]
        )
        run_p50s = [
            report["metrics"]["summaries"][key]["p50_ms"]
            for report in reports
        ]
        per_run[key] = {
            "p50_min_ms": min(run_p50s),
            "p50_median_ms": summarize(run_p50s)["p50_ms"],
            "p50_max_ms": max(run_p50s),
        }

    paired_directions = {}
    for artifact in ("published", "rebuilt"):
        positive = sum(
            report["metrics"]["paired_path_deltas"][artifact][
                "positive_blocks"
            ]
            for report in reports
        )
        total = sum(
            report["metrics"]["paired_path_deltas"][artifact][
                "fresh_minus_stable_ms"
            ]["count"]
            for report in reports
        )
        paired_directions[artifact] = {
            "fresh_slower_blocks": positive,
            "total_blocks": total,
        }

    all_gates_passed = all(report["gate"]["passed"] for report in reports)
    return {
        "schema_version": "sri.experiment.native-path-launch-summary.v1",
        "experiment": {
            "name": "native-sender-path-reuse-launch-repeated-summary",
            "evidence_grade": "Derived",
            "limitations": [
                "Runs are repeated on one host and are not independent machines.",
                "Blocks within a run share binaries, caches, and scheduling context.",
                "Pooled latency and direction counts are descriptive, not causal estimates.",
            ],
        },
        "metrics": {
            "report_count": len(reports),
            "total_trials": len(all_rows),
            "correct_trials": sum(row["passed"] for row in all_rows),
            "all_run_gates_passed": all_gates_passed,
            "pooled_summaries": pooled,
            "per_run_p50_ranges": per_run,
            "paired_directions": paired_directions,
        },
        "gate": {
            "name": "three-run path launch integrity summary",
            "passed": (
                len(reports) >= 3
                and all_gates_passed
                and all(row["passed"] for row in all_rows)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    loaded = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in arguments.reports
    ]
    report = summarize_reports(loaded)
    output = write_report(
        EXPERIMENT_DIR,
        "native-path-launch-summary",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
