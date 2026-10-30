#!/usr/bin/env python3
"""Freeze selected-only review cases from producer output."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.causal_claim_classifier_benchmark import (
    classify_claim_fail_closed_v3,
)


def prepare(cases_path: Path, producer_path: Path) -> tuple[dict, list[dict]]:
    cases = load_jsonl(cases_path)
    producer = json.loads(producer_path.read_text(encoding="utf-8"))
    if producer["experiment"]["dataset_sha256"] != sha256_path(cases_path):
        raise ValueError("producer and case corpus digest differ")
    rows = {
        row["case_id"]: row
        for row in producer["trials"]
        if row["mode"] == "structured"
    }
    selections = []
    selected_cases = []
    for case in cases:
        row = rows.get(case["case_id"])
        completed = bool(row and row["status"] == "completed")
        producer_allowed = bool(completed and row["predicted_allowed"])
        local = classify_claim_fail_closed_v3(case["text"])
        selected = bool(
            producer_allowed
            and local["claim_kind"] != "unknown"
            and local["claim_kind"] != row["predicted_claim_kind"]
        )
        selections.append(
            {
                "case_id": case["case_id"],
                "producer_completed": completed,
                "producer_claim_kind": (
                    row.get("predicted_claim_kind")
                    if completed
                    else "unavailable"
                ),
                "producer_allowed": producer_allowed,
                "local_router_claim_kind": local["claim_kind"],
                "selected": selected,
            }
        )
        if selected:
            selected_cases.append(case)
    report = {
        "schema_version": "sri.experiment.prospective-review-queue.v1",
        "experiment": {
            "name": "frozen-v3-local-conflict-selected-only-queue",
            "evidence_grade": "derived",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "producer_report_path": str(producer_path.resolve()),
            "producer_report_sha256": sha256_path(producer_path),
            "selection_timing": (
                "manifest frozen after producer completion and before any "
                "selected-only or shadow verifier execution"
            ),
        },
        "metrics": {
            "case_count": len(cases),
            "selected_count": len(selected_cases),
            "selection_rate": (
                len(selected_cases) / len(cases) if cases else 0.0
            ),
        },
        "selections": selections,
    }
    return report, selected_cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--producer-report", required=True, type=Path)
    parser.add_argument("--selected-cases", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report, selected_cases = prepare(
        arguments.cases, arguments.producer_report
    )
    with arguments.selected_cases.open("w", encoding="utf-8") as stream:
        for case in selected_cases:
            stream.write(json.dumps(case, ensure_ascii=False) + "\n")
    report["experiment"]["selected_cases_path"] = str(
        arguments.selected_cases.resolve()
    )
    report["experiment"]["selected_cases_sha256"] = sha256_path(
        arguments.selected_cases
    )
    output = write_report(
        EXPERIMENT_DIR,
        "prospective-review-queue",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Selected cases: {arguments.selected_cases}")
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
