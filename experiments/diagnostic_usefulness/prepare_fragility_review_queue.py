#!/usr/bin/env python3
"""Freeze fragility-selected and random unselected shadow queues."""

import argparse
import json
import math
import random
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.analyze_contract_fragility_router import (
    authorization_fragility,
)


def prepare(
    cases_path: Path,
    producer_path: Path,
    threshold: float,
    shadow_rate: float,
    shadow_seed: int,
) -> tuple[dict, list[dict], list[dict]]:
    if not 0.0 < shadow_rate <= 1.0:
        raise ValueError("shadow_rate must be in (0, 1]")
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
    selected_ids = set()
    for case in cases:
        row = rows.get(case["case_id"])
        completed = bool(row and row["status"] == "completed")
        allowed = bool(completed and row["predicted_allowed"])
        fragility = (
            authorization_fragility(
                case["causal_scope"], row["predicted_claim_kind"]
            )
            if completed
            else 1.0
        )
        selected = allowed and fragility >= threshold
        if selected:
            selected_ids.add(case["case_id"])
        selections.append(
            {
                "case_id": case["case_id"],
                "producer_completed": completed,
                "producer_claim_kind": (
                    row.get("predicted_claim_kind")
                    if completed
                    else "unavailable"
                ),
                "producer_allowed": allowed,
                "authorization_fragility": fragility,
                "selected": selected,
            }
        )
    unselected_ids = sorted(
        case["case_id"]
        for case in cases
        if case["case_id"] not in selected_ids
    )
    shadow_count = (
        min(
            len(unselected_ids),
            max(1, math.ceil(len(unselected_ids) * shadow_rate)),
        )
        if unselected_ids
        else 0
    )
    shadow_ids = set(
        random.Random(shadow_seed).sample(unselected_ids, shadow_count)
    )
    selected_cases = [
        case for case in cases if case["case_id"] in selected_ids
    ]
    shadow_cases = [
        case for case in cases if case["case_id"] in shadow_ids
    ]
    for row in selections:
        row["random_shadow_selected"] = row["case_id"] in shadow_ids
    report = {
        "schema_version": "sri.experiment.fragility-review-queue.v1",
        "experiment": {
            "name": "prospective-fragility-selected-plus-random-shadow",
            "evidence_grade": "derived",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "producer_report_path": str(producer_path.resolve()),
            "producer_report_sha256": sha256_path(producer_path),
            "fragility_threshold": threshold,
            "random_shadow_rate": shadow_rate,
            "random_shadow_seed": shadow_seed,
            "selection_timing": (
                "selected and random-shadow manifests frozen after producer "
                "completion and before any verifier execution"
            ),
        },
        "metrics": {
            "case_count": len(cases),
            "selected_count": len(selected_cases),
            "selection_rate": (
                len(selected_cases) / len(cases) if cases else 0.0
            ),
            "unselected_count": len(unselected_ids),
            "random_shadow_count": len(shadow_cases),
            "realized_random_shadow_rate": (
                len(shadow_cases) / len(unselected_ids)
                if unselected_ids
                else 0.0
            ),
        },
        "selections": selections,
    }
    return report, selected_cases, shadow_cases


def _write_jsonl(path: Path, cases: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for case in cases:
            stream.write(json.dumps(case, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--producer-report", required=True, type=Path)
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--shadow-rate", type=float, default=0.25)
    parser.add_argument("--shadow-seed", type=int, default=20260731)
    parser.add_argument("--selected-cases", required=True, type=Path)
    parser.add_argument("--shadow-cases", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report, selected_cases, shadow_cases = prepare(
        arguments.cases,
        arguments.producer_report,
        arguments.threshold,
        arguments.shadow_rate,
        arguments.shadow_seed,
    )
    _write_jsonl(arguments.selected_cases, selected_cases)
    _write_jsonl(arguments.shadow_cases, shadow_cases)
    report["experiment"].update(
        {
            "selected_cases_path": str(arguments.selected_cases.resolve()),
            "selected_cases_sha256": sha256_path(arguments.selected_cases),
            "shadow_cases_path": str(arguments.shadow_cases.resolve()),
            "shadow_cases_sha256": sha256_path(arguments.shadow_cases),
        }
    )
    output = write_report(
        EXPERIMENT_DIR,
        "fragility-review-queue",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Selected cases: {arguments.selected_cases}")
    print(f"Shadow cases: {arguments.shadow_cases}")
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
