#!/usr/bin/env python3
"""Analyze selected-only review against an independent always-on shadow."""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.run_claim_output_mode_study import (
    _prompt,
)


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
    selected_verifier_path: Path,
    shadow_verifier_path: Path,
) -> Dict[str, Any]:
    cases = load_jsonl(cases_path)
    digest = sha256_path(cases_path)
    producer = json.loads(producer_path.read_text(encoding="utf-8"))
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    selected_report = json.loads(
        selected_verifier_path.read_text(encoding="utf-8")
    )
    shadow_report = json.loads(
        shadow_verifier_path.read_text(encoding="utf-8")
    )
    if producer["experiment"]["dataset_sha256"] != digest:
        raise ValueError("producer dataset mismatch")
    if queue["experiment"]["dataset_sha256"] != digest:
        raise ValueError("queue dataset mismatch")
    if shadow_report["experiment"]["dataset_sha256"] != digest:
        raise ValueError("shadow dataset mismatch")
    if queue["experiment"]["producer_report_sha256"] != sha256_path(
        producer_path
    ):
        raise ValueError("queue was not frozen from this producer report")
    if queue["experiment"]["selected_cases_sha256"] != selected_report[
        "experiment"
    ]["dataset_sha256"]:
        raise ValueError("selected verifier dataset differs from queue")
    producer_rows = _rows(producer)
    selected_rows = _rows(selected_report)
    shadow_rows = _rows(shadow_report)
    selections = {
        row["case_id"]: row["selected"] for row in queue["selections"]
    }
    rows = []
    for case in cases:
        producer_row = producer_rows[case["case_id"]]
        shadow_row = shadow_rows[case["case_id"]]
        selected = bool(selections[case["case_id"]])
        selected_row = selected_rows.get(case["case_id"])
        producer_completed = producer_row["status"] == "completed"
        selected_completed = bool(
            selected_row and selected_row["status"] == "completed"
        )
        shadow_completed = shadow_row["status"] == "completed"
        producer_allowed = bool(
            producer_completed and producer_row["predicted_allowed"]
        )
        selected_allowed = bool(
            selected_completed and selected_row["predicted_allowed"]
        )
        shadow_allowed = bool(
            shadow_completed and shadow_row["predicted_allowed"]
        )
        routed_allowed = bool(
            producer_allowed
            and (not selected or selected_allowed)
        )
        always_on_allowed = producer_allowed and shadow_allowed
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_allowed": case["expected_allowed"],
                "selected": selected,
                "producer_claim_kind": producer_row.get(
                    "predicted_claim_kind", "unavailable"
                ),
                "producer_allowed": producer_allowed,
                "selected_verifier_claim_kind": (
                    selected_row.get("predicted_claim_kind")
                    if selected_completed
                    else "not_invoked"
                ),
                "routed_allowed": routed_allowed,
                "shadow_claim_kind": shadow_row.get(
                    "predicted_claim_kind", "unavailable"
                ),
                "always_on_allowed": always_on_allowed,
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
                "always_on_false_allow": (
                    not case["expected_allowed"] and always_on_allowed
                ),
                "always_on_false_deny": (
                    case["expected_allowed"] and not always_on_allowed
                ),
                "producer_elapsed_ms": producer_row["elapsed_ms"],
                "selected_verifier_elapsed_ms": (
                    selected_row["elapsed_ms"] if selected_completed else 0.0
                ),
                "shadow_elapsed_ms": shadow_row["elapsed_ms"],
                "routed_serial_path_ms": (
                    producer_row["elapsed_ms"]
                    + (
                        selected_row["elapsed_ms"]
                        if selected_completed
                        else 0.0
                    )
                ),
                "always_on_serial_path_ms": (
                    producer_row["elapsed_ms"] + shadow_row["elapsed_ms"]
                ),
            }
        )
    selected_completed_rows = [
        row
        for row in selected_report["trials"]
        if row["status"] == "completed"
    ]
    shadow_completed_rows = [
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
        "always_on_false_allows": sum(
            row["always_on_false_allow"] for row in rows
        ),
        "always_on_false_denies": sum(
            row["always_on_false_deny"] for row in rows
        ),
        "router_captured_false_allows": sum(
            row["baseline_false_allow"]
            and not row["routed_false_allow"]
            for row in rows
        ),
        "router_missed_false_allows": sum(
            row["baseline_false_allow"] and row["routed_false_allow"]
            for row in rows
        ),
        "always_on_captured_false_allows": sum(
            row["baseline_false_allow"]
            and not row["always_on_false_allow"]
            for row in rows
        ),
        "selected_verifier_input_tokens": sum(
            int(row.get("usage", {}).get("input", 0))
            for row in selected_completed_rows
        ),
        "selected_verifier_total_tokens": sum(
            int(row.get("usage", {}).get("total", 0))
            for row in selected_completed_rows
        ),
        "shadow_verifier_input_tokens": sum(
            int(row.get("usage", {}).get("input", 0))
            for row in shadow_completed_rows
        ),
        "shadow_verifier_total_tokens": sum(
            int(row.get("usage", {}).get("total", 0))
            for row in shadow_completed_rows
        ),
        "selected_prompt_bytes": sum(
            len(_prompt(case, "structured").encode("utf-8"))
            for case in cases
            if selections[case["case_id"]]
        ),
        "shadow_prompt_bytes": sum(
            len(_prompt(case, "structured").encode("utf-8"))
            for case in cases
        ),
        "producer_latency_p50_ms": statistics.median(
            row["producer_elapsed_ms"] for row in rows
        ),
        "routed_computed_serial_path_p50_ms": statistics.median(
            row["routed_serial_path_ms"] for row in rows
        ),
        "always_on_computed_serial_path_p50_ms": statistics.median(
            row["always_on_serial_path_ms"] for row in rows
        ),
    }
    return {
        "schema_version": "sri.experiment.prospective-review-study.v1",
        "experiment": {
            "name": "prospective-selected-only-versus-always-on-shadow",
            "evidence_grade": "experimental",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": digest,
            "producer_report_path": str(producer_path.resolve()),
            "producer_report_sha256": sha256_path(producer_path),
            "queue_report_path": str(queue_path.resolve()),
            "queue_report_sha256": sha256_path(queue_path),
            "selected_verifier_report_path": str(
                selected_verifier_path.resolve()
            ),
            "selected_verifier_report_sha256": sha256_path(
                selected_verifier_path
            ),
            "shadow_verifier_report_path": str(
                shadow_verifier_path.resolve()
            ),
            "shadow_verifier_report_sha256": sha256_path(
                shadow_verifier_path
            ),
            "limitations": [
                "The holdout is hand-authored and has one response per model and case.",
                "Selected-only and shadow verifier calls use separate fresh sessions, so per-case verifier outputs are not paired identical responses.",
                "Serial path values are computed from observed per-call latency; the batch execution schedules differ.",
                "The two recorded model IDs do not independently prove model-family or provider independence.",
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
    parser.add_argument("--selected-verifier-report", required=True, type=Path)
    parser.add_argument("--shadow-verifier-report", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = analyze(
        arguments.cases,
        arguments.producer_report,
        arguments.queue_report,
        arguments.selected_verifier_report,
        arguments.shadow_verifier_report,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "prospective-review-study",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
