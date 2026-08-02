#!/usr/bin/env python3
"""Recompute structured-model authorization with a deny-only verifier."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.causal_claim_classifier_benchmark import (
    classify_claim_fail_closed_v3,
)
from skill_runtime_intelligence.diagnostics import validate_causal_claim


def analyze(report_path: Path, cases_path: Path) -> Dict[str, Any]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("schema_version") != (
        "sri.experiment.claim-output-mode-study.v1"
    ):
        raise ValueError("unsupported model-study report schema")
    cases = {case["case_id"]: case for case in load_jsonl(cases_path)}
    if report["experiment"]["dataset_sha256"] != sha256_path(cases_path):
        raise ValueError("model report and case corpus digest differ")
    rows: List[Dict[str, Any]] = []
    for trial in report["trials"]:
        if trial["mode"] != "structured" or trial["status"] != "completed":
            continue
        case = cases[trial["case_id"]]
        verifier = classify_claim_fail_closed_v3(case["text"])
        verifier_guard = validate_causal_claim(
            case["causal_scope"], verifier["claim_kind"]
        )
        baseline_allowed = bool(trial["predicted_allowed"])
        hybrid_allowed = baseline_allowed and verifier_guard["allowed"]
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_allowed": case["expected_allowed"],
                "model_claim_kind": trial["predicted_claim_kind"],
                "baseline_allowed": baseline_allowed,
                "verifier_claim_kind": verifier["claim_kind"],
                "verifier_basis": verifier["basis"],
                "verifier_allowed": verifier_guard["allowed"],
                "hybrid_allowed": hybrid_allowed,
                "baseline_false_allow": (
                    not case["expected_allowed"] and baseline_allowed
                ),
                "baseline_false_deny": (
                    case["expected_allowed"] and not baseline_allowed
                ),
                "hybrid_false_allow": (
                    not case["expected_allowed"] and hybrid_allowed
                ),
                "hybrid_false_deny": (
                    case["expected_allowed"] and not hybrid_allowed
                ),
            }
        )
    metrics = {
        "completed_structured_trials": len(rows),
        "baseline_false_allows": sum(
            row["baseline_false_allow"] for row in rows
        ),
        "baseline_false_denies": sum(
            row["baseline_false_deny"] for row in rows
        ),
        "hybrid_false_allows": sum(
            row["hybrid_false_allow"] for row in rows
        ),
        "hybrid_false_denies": sum(
            row["hybrid_false_deny"] for row in rows
        ),
        "verifier_unknowns": sum(
            row["verifier_claim_kind"] == "unknown" for row in rows
        ),
        "hybrid_changed_decisions": sum(
            row["baseline_allowed"] != row["hybrid_allowed"]
            for row in rows
        ),
    }
    return {
        "schema_version": "sri.experiment.deny-only-hybrid.v1",
        "experiment": {
            "name": "structured-model-plus-deny-only-verifier",
            "evidence_grade": "experimental",
            "model": report["experiment"]["model"],
            "model_report_path": str(report_path.resolve()),
            "model_report_sha256": sha256_path(report_path),
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "combination_rule": (
                "allow only when model-derived scope guard and frozen "
                "fail-closed-v3 verifier both allow"
            ),
            "limitations": [
                "This is a post-hoc policy replay, not a randomized product-effect estimate.",
                "The verifier is a small phrase matcher and is not a semantic trust root.",
                "Safety and usability errors must be reported separately.",
            ],
        },
        "metrics": metrics,
        "cases": rows,
        "gates": {
            "no_hybrid_false_allow": metrics["hybrid_false_allows"] == 0,
            "no_hybrid_false_deny": metrics["hybrid_false_denies"] == 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    result = analyze(arguments.report, arguments.cases)
    output = write_report(
        EXPERIMENT_DIR,
        "deny-only-hybrid",
        result,
        arguments.output,
    )
    print(json.dumps(result["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
