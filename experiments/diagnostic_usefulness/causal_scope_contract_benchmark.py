#!/usr/bin/env python3
"""Audit the deterministic causal-scope contract over diagnostic findings."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.runtime_diagnostics.run_benchmark import _materialize_run
from skill_runtime_intelligence.diagnostics import (
    CAUSAL_CLAIM_KINDS,
    CAUSAL_SCOPES,
    diagnose_skill_run,
    validate_causal_claim,
)


def run_benchmark(cases_path: Path) -> dict:
    cases = [
        case for case in load_jsonl(cases_path) if case["expected_findings"]
    ]
    findings = []
    for case in cases:
        for finding in diagnose_skill_run(_materialize_run(case["run"])):
            findings.append({"case_id": case["case_id"], **finding})
    current_checks = []
    for finding in findings:
        for claim_kind in CAUSAL_CLAIM_KINDS:
            result = validate_causal_claim(
                finding["causal_scope"], claim_kind
            )
            current_checks.append(
                {
                    "case_id": finding["case_id"],
                    "finding_code": finding["code"],
                    **result,
                }
            )
    policy_checks = []
    expected_allowed = {
        "none": {"descriptive"},
        "source_assertion_only": {
            "descriptive",
            "source_attribution",
        },
        "experimental_estimate": set(CAUSAL_CLAIM_KINDS),
    }
    for scope in CAUSAL_SCOPES:
        for claim_kind in CAUSAL_CLAIM_KINDS:
            result = validate_causal_claim(scope, claim_kind)
            policy_checks.append(
                {
                    **result,
                    "expected_allowed": claim_kind
                    in expected_allowed[scope],
                }
            )
    invalid_checks = [
        validate_causal_claim("unknown", "skill_outcome_effect"),
        validate_causal_claim("none", "unknown"),
    ]
    current_effect_checks = [
        check
        for check in current_checks
        if check["claim_kind"] == "skill_outcome_effect"
    ]
    metrics = {
        "case_count": len(cases),
        "finding_count": len(findings),
        "single_run_findings_with_none_scope": sum(
            finding["causal_scope"] == "none" for finding in findings
        ),
        "single_run_effect_claims_allowed": sum(
            check["allowed"] for check in current_effect_checks
        ),
        "single_run_descriptive_claims_allowed": sum(
            check["allowed"]
            for check in current_checks
            if check["claim_kind"] == "descriptive"
        ),
        "policy_matrix_exact": sum(
            check["allowed"] == check["expected_allowed"]
            for check in policy_checks
        ),
        "policy_matrix_total": len(policy_checks),
        "invalid_inputs_denied": sum(
            not check["allowed"] for check in invalid_checks
        ),
        "invalid_input_count": len(invalid_checks),
    }
    passed = (
        metrics["single_run_findings_with_none_scope"]
        == metrics["finding_count"]
        and metrics["single_run_effect_claims_allowed"] == 0
        and metrics["single_run_descriptive_claims_allowed"]
        == metrics["finding_count"]
        and metrics["policy_matrix_exact"]
        == metrics["policy_matrix_total"]
        and metrics["invalid_inputs_denied"]
        == metrics["invalid_input_count"]
    )
    return {
        "schema_version": "sri.experiment.causal-scope-contract.v1",
        "experiment": {
            "name": "deterministic-causal-scope-contract",
            "evidence_grade": "derived",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "limitations": [
                "The benchmark validates policy mechanics, not whether natural-language claims are classified correctly.",
                "The corpus is synthetic and contains no experimental-effect Finding.",
            ],
        },
        "metrics": metrics,
        "policy_checks": policy_checks,
        "invalid_checks": invalid_checks,
        "gate": {"name": "causal-scope contract", "passed": passed},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=REPOSITORY_ROOT
        / "experiments"
        / "runtime_diagnostics"
        / "cases.jsonl",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(arguments.cases)
    output = write_report(
        EXPERIMENT_DIR,
        "causal-scope-contract",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "gate_passed": report["gate"]["passed"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
