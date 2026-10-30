#!/usr/bin/env python3
"""Analyze prospective fragility routing plus random unselected shadow."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import load_jsonl, sha256_path, write_report


def _rows(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["case_id"]: row
        for row in report["trials"]
        if row["mode"] == "structured"
    }


def analyze(
    cases_path: Path,
    producer_path: Path,
    queue_path: Path,
    selected_path: Path,
    shadow_path: Path,
) -> Dict[str, Any]:
    cases = load_jsonl(cases_path)
    digest = sha256_path(cases_path)
    producer = json.loads(producer_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    selected_report = json.loads(selected_path.read_text(encoding="utf-8"))
    shadow_report = json.loads(shadow_path.read_text(encoding="utf-8"))
    if producer["experiment"]["dataset_sha256"] != digest:
        raise ValueError("producer dataset mismatch")
    if queue["experiment"]["dataset_sha256"] != digest:
        raise ValueError("queue dataset mismatch")
    if queue["experiment"]["producer_report_sha256"] != sha256_path(
        producer_path
    ):
        raise ValueError("queue was not frozen from this producer")
    if queue["experiment"]["selected_cases_sha256"] != selected_report[
        "experiment"
    ]["dataset_sha256"]:
        raise ValueError("selected verifier dataset mismatch")
    if queue["experiment"]["shadow_cases_sha256"] != shadow_report[
        "experiment"
    ]["dataset_sha256"]:
        raise ValueError("shadow verifier dataset mismatch")
    producer_rows = _rows(producer)
    selected_rows = _rows(selected_report)
    shadow_rows = _rows(shadow_report)
    selections = {
        row["case_id"]: row for row in queue["selections"]
    }
    rows = []
    for case in cases:
        selection = selections[case["case_id"]]
        producer_row = producer_rows[case["case_id"]]
        selected = bool(selection["selected"])
        shadowed = bool(selection["random_shadow_selected"])
        selected_row = selected_rows.get(case["case_id"])
        shadow_row = shadow_rows.get(case["case_id"])
        producer_allowed = bool(producer_row["predicted_allowed"])
        selected_allowed = bool(
            selected_row and selected_row["predicted_allowed"]
        )
        routed_allowed = bool(
            producer_allowed and (not selected or selected_allowed)
        )
        shadow_allowed = (
            bool(shadow_row["predicted_allowed"]) if shadow_row else None
        )
        rows.append(
            {
                "case_id": case["case_id"],
                "causal_scope": case["causal_scope"],
                "expected_claim_kind": case["expected_claim_kind"],
                "tags": case["tags"],
                "expected_allowed": case["expected_allowed"],
                "producer_claim_kind": producer_row[
                    "predicted_claim_kind"
                ],
                "producer_allowed": producer_allowed,
                "authorization_fragility": selection[
                    "authorization_fragility"
                ],
                "selected": selected,
                "selected_verifier_claim_kind": (
                    selected_row["predicted_claim_kind"]
                    if selected_row
                    else "not_invoked"
                ),
                "routed_allowed": routed_allowed,
                "random_shadow_selected": shadowed,
                "shadow_claim_kind": (
                    shadow_row["predicted_claim_kind"]
                    if shadow_row
                    else "not_sampled"
                ),
                "shadow_allowed": shadow_allowed,
                "shadow_semantic_disagreement": bool(
                    shadow_row
                    and producer_row["predicted_claim_kind"]
                    != shadow_row["predicted_claim_kind"]
                ),
                "baseline_false_allow": (
                    not case["expected_allowed"] and producer_allowed
                ),
                "baseline_false_deny": (
                    case["expected_allowed"] and not producer_allowed
                ),
                "routed_false_allow": (
                    not case["expected_allowed"] and routed_allowed
                ),
                "routed_false_deny": (
                    case["expected_allowed"] and not routed_allowed
                ),
                "shadow_guard_error": bool(
                    shadow_row
                    and shadow_allowed != case["expected_allowed"]
                ),
            }
        )
    selected_trials = [
        row
        for row in selected_report["trials"]
        if row["status"] == "completed"
    ]
    shadow_trials = [
        row
        for row in shadow_report["trials"]
        if row["status"] == "completed"
    ]
    metrics = {
        "case_count": len(rows),
        "selected_count": sum(row["selected"] for row in rows),
        "selection_rate": (
            sum(row["selected"] for row in rows) / len(rows)
            if rows
            else 0.0
        ),
        "random_shadow_count": sum(
            row["random_shadow_selected"] for row in rows
        ),
        "total_verifier_calls": len(selected_trials) + len(shadow_trials),
        "baseline_false_allows": sum(
            row["baseline_false_allow"] for row in rows
        ),
        "baseline_false_denies": sum(
            row["baseline_false_deny"] for row in rows
        ),
        "routed_false_allows": sum(
            row["routed_false_allow"] for row in rows
        ),
        "routed_false_denies": sum(
            row["routed_false_deny"] for row in rows
        ),
        "captured_false_allows": sum(
            row["baseline_false_allow"]
            and not row["routed_false_allow"]
            for row in rows
        ),
        "missed_false_allows": sum(
            row["baseline_false_allow"] and row["routed_false_allow"]
            for row in rows
        ),
        "unselected_baseline_false_allows": sum(
            row["baseline_false_allow"] and not row["selected"]
            for row in rows
        ),
        "shadow_semantic_disagreements": sum(
            row["shadow_semantic_disagreement"] for row in rows
        ),
        "shadow_guard_errors": sum(
            row["shadow_guard_error"] for row in rows
        ),
        "selected_input_tokens": sum(
            int(row.get("usage", {}).get("input", 0))
            for row in selected_trials
        ),
        "selected_total_tokens": sum(
            int(row.get("usage", {}).get("total", 0))
            for row in selected_trials
        ),
        "shadow_input_tokens": sum(
            int(row.get("usage", {}).get("input", 0))
            for row in shadow_trials
        ),
        "shadow_total_tokens": sum(
            int(row.get("usage", {}).get("total", 0))
            for row in shadow_trials
        ),
    }
    return {
        "schema_version": "sri.experiment.prospective-fragility-study.v1",
        "experiment": {
            "name": (
                "prospective-contract-fragility-selected-plus-random-shadow"
            ),
            "evidence_grade": "experimental",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": digest,
            "producer_report_sha256": sha256_path(producer_path),
            "queue_report_sha256": sha256_path(queue_path),
            "selected_report_sha256": sha256_path(selected_path),
            "shadow_report_sha256": sha256_path(shadow_path),
            "limitations": [
                "The corpus is hand-authored with one response per model and case.",
                "The three-case random shadow is too small for a population blind-spot estimate.",
                "Selected and shadow verifier outputs come from separate fresh sessions.",
                "The recorded model IDs do not prove independent model families or providers.",
            ],
        },
        "metrics": metrics,
        "cases": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--producer-report", required=True, type=Path)
    parser.add_argument("--queue-report", required=True, type=Path)
    parser.add_argument("--selected-report", required=True, type=Path)
    parser.add_argument("--shadow-report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = analyze(
        arguments.cases,
        arguments.producer_report,
        arguments.queue_report,
        arguments.selected_report,
        arguments.shadow_report,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "prospective-fragility-study",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
