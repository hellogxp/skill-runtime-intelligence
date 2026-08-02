#!/usr/bin/env python3
"""Summarize repeated launch-factor runs while preserving run boundaries."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.product_lifecycle.native_sender_launch_factor_benchmark import (
    summarize,
)


def summarize_reports(reports: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if not reports:
        raise ValueError("at least one report is required")
    expected = "native-sender-placement-signature-factorial"
    if any(
        report.get("experiment", {}).get("name") != expected
        for report in reports
    ):
        raise ValueError("report experiment name mismatch")
    rows = [
        row
        for report in reports
        for row in report.get("trials", [])
    ]
    cell_keys = sorted(reports[0]["metrics"]["cell_summaries"])
    pooled_cells = {}
    per_run_cells = {}
    for key in cell_keys:
        placement, provenance, signature = key.split(":")
        pooled_cells[key] = summarize(
            [
                row["wall_ms"]
                for row in rows
                if row["placement"] == placement
                and row["provenance"] == provenance
                and row["signature"] == signature
            ]
        )
        p50s = [
            report["metrics"]["cell_summaries"][key]["p50_ms"]
            for report in reports
        ]
        per_run_cells[key] = {
            "p50_values_ms": p50s,
            "p50_range_ms": [min(p50s), max(p50s)],
        }

    factor_boundaries = {}
    for factor in ("placement", "signature"):
        delta_p50s = [
            report["metrics"]["factor_deltas"][factor]["delta_ms"]["p50_ms"]
            for report in reports
        ]
        positive_blocks = [
            report["metrics"]["factor_deltas"][factor]["positive_blocks"]
            for report in reports
        ]
        blocks = [
            report["metrics"]["factor_deltas"][factor]["delta_ms"]["count"]
            for report in reports
        ]
        factor_boundaries[factor] = {
            "contrast": reports[0]["metrics"]["factor_deltas"][factor][
                "contrast"
            ],
            "per_run_delta_p50_ms": delta_p50s,
            "delta_p50_range_ms": [min(delta_p50s), max(delta_p50s)],
            "positive_blocks_by_run": positive_blocks,
            "positive_blocks_total": sum(positive_blocks),
            "total_blocks": sum(blocks),
            "direction_consistent_across_run_p50s": (
                all(value > 0 for value in delta_p50s)
                or all(value < 0 for value in delta_p50s)
            ),
        }

    all_gates = all(report["gate"]["passed"] for report in reports)
    correct = sum(row["passed"] for row in rows)
    setup = sum(row["factor_setup"]["passed"] for row in rows)
    return {
        "schema_version": "sri.experiment.native-launch-factor-summary.v1",
        "experiment": {
            "name": "native-sender-placement-signature-repeated-summary",
            "evidence_grade": "Derived",
            "limitations": [
                "Three runs share one host and are not independent machines.",
                "Strong run-order differences make pooled latency nonstationary.",
                "Factor manipulations do not identify the host mechanism.",
                "Integrity passes do not imply a stable latency effect.",
            ],
        },
        "metrics": {
            "report_count": len(reports),
            "total_trials": len(rows),
            "correct_trials": correct,
            "factor_setup_passed_trials": setup,
            "all_run_gates_passed": all_gates,
            "pooled_cell_summaries": pooled_cells,
            "per_run_cell_boundaries": per_run_cells,
            "factor_run_boundaries": factor_boundaries,
        },
        "gate": {
            "name": "three-run launch-factor integrity summary",
            "passed": (
                len(reports) >= 3
                and all_gates
                and correct == len(rows)
                and setup == len(rows)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    reports = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in arguments.reports
    ]
    report = summarize_reports(reports)
    output = write_report(
        EXPERIMENT_DIR,
        "native-launch-factor-summary",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
