#!/usr/bin/env python3
"""Summarize cut-policy stability and retention by observation interval."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.real_corpus_audit.summarize_cut_policy_reports import (
    _aggregate,
)


def _curve(reports: list) -> Dict[str, Any]:
    grouped = defaultdict(list)
    for report in reports:
        interval = float(report["experiment"]["requested_interval_seconds"])
        grouped[interval].append(report)
    points = []
    for interval in sorted(grouped):
        aggregate = _aggregate(grouped[interval])
        points.append(
            {
                "requested_interval_seconds": interval,
                "trial_count": aggregate["trial_count"],
                "policies": aggregate["policies"],
            }
        )
    return {
        "interval_condition_count": len(points),
        "trial_count": len(reports),
        "points": points,
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
    curve = _curve(reports)
    enough_repeats = all(
        point["trial_count"] >= 2 for point in curve["points"]
    )
    report = {
        "schema_version": "sri.experiment.dataset-cut-policy-curve.v1",
        "experiment": {
            "name": "privacy-safe-cut-policy-wait-curve",
            "evidence_grade": "Experimental",
            "row_level_records_included": False,
            "limitations": [
                "Intervals were observed sequentially, not randomized.",
                "Ambient ingestion load can differ between interval conditions.",
                "Repeated run observations are not independent participants.",
                "The curve does not estimate a causal waiting-time effect.",
            ],
        },
        "curve": curve,
        "gate": {
            "name": "multi-interval cut-policy curve completed",
            "passed": (
                source_gates_passed
                and curve["interval_condition_count"] >= 2
                and enough_repeats
            ),
        },
    }
    output = write_report(
        EXPERIMENT_DIR,
        "dataset-cut-policy-curve",
        report,
        arguments.output,
    )
    print(json.dumps({"curve": curve, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
