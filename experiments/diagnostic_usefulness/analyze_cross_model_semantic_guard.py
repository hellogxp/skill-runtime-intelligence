#!/usr/bin/env python3
"""Evaluate a symmetric cross-model deny-only semantic guard."""

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
from skill_runtime_intelligence.diagnostics import validate_causal_claim


SCHEMA = "sri.experiment.claim-output-mode-study.v1"


def _load_report(path: Path, dataset_sha256: str) -> Dict[str, Any]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema_version") != SCHEMA:
        raise ValueError(f"unsupported report schema: {path}")
    if report["experiment"]["dataset_sha256"] != dataset_sha256:
        raise ValueError(f"dataset digest mismatch: {path}")
    return report


def _structured_by_case(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["case_id"]: row
        for row in report["trials"]
        if row["mode"] == "structured"
    }


def _direction(
    cases: List[Dict[str, Any]],
    producer: Dict[str, Any],
    verifier: Dict[str, Any],
) -> Dict[str, Any]:
    producer_rows = _structured_by_case(producer)
    verifier_rows = _structured_by_case(verifier)
    rows = []
    for case in cases:
        producer_row = producer_rows.get(case["case_id"])
        verifier_row = verifier_rows.get(case["case_id"])
        producer_completed = bool(
            producer_row and producer_row["status"] == "completed"
        )
        verifier_completed = bool(
            verifier_row and verifier_row["status"] == "completed"
        )
        producer_allowed = bool(
            producer_completed and producer_row["predicted_allowed"]
        )
        verifier_allowed = bool(
            verifier_completed
            and validate_causal_claim(
                case["causal_scope"],
                verifier_row["predicted_claim_kind"],
            )["allowed"]
        )
        hybrid_allowed = producer_allowed and verifier_allowed
        semantic_agreement = bool(
            producer_completed
            and verifier_completed
            and producer_row["predicted_claim_kind"]
            == verifier_row["predicted_claim_kind"]
        )
        exact_kind_consensus_allowed = hybrid_allowed and semantic_agreement
        rows.append(
            {
                "case_id": case["case_id"],
                "expected_allowed": case["expected_allowed"],
                "producer_completed": producer_completed,
                "producer_claim_kind": (
                    producer_row.get("predicted_claim_kind")
                    if producer_completed
                    else "unavailable"
                ),
                "producer_allowed": producer_allowed,
                "verifier_completed": verifier_completed,
                "verifier_claim_kind": (
                    verifier_row.get("predicted_claim_kind")
                    if verifier_completed
                    else "unavailable"
                ),
                "verifier_allowed": verifier_allowed,
                "hybrid_allowed": hybrid_allowed,
                "semantic_disagreement": (
                    producer_completed
                    and verifier_completed
                    and not semantic_agreement
                ),
                "baseline_false_allow": (
                    not case["expected_allowed"] and producer_allowed
                ),
                "baseline_false_deny": (
                    case["expected_allowed"] and not producer_allowed
                ),
                "hybrid_false_allow": (
                    not case["expected_allowed"] and hybrid_allowed
                ),
                "hybrid_false_deny": (
                    case["expected_allowed"] and not hybrid_allowed
                ),
                "exact_kind_consensus_allowed": (
                    exact_kind_consensus_allowed
                ),
                "exact_kind_consensus_false_allow": (
                    not case["expected_allowed"]
                    and exact_kind_consensus_allowed
                ),
                "exact_kind_consensus_false_deny": (
                    case["expected_allowed"]
                    and not exact_kind_consensus_allowed
                ),
            }
        )
    metrics = {
        "case_count": len(rows),
        "producer_completed": sum(row["producer_completed"] for row in rows),
        "verifier_completed": sum(row["verifier_completed"] for row in rows),
        "semantic_disagreements": sum(
            row["semantic_disagreement"] for row in rows
        ),
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
        "hybrid_changed_decisions": sum(
            row["producer_allowed"] != row["hybrid_allowed"]
            for row in rows
        ),
        "exact_kind_consensus_false_allows": sum(
            row["exact_kind_consensus_false_allow"] for row in rows
        ),
        "exact_kind_consensus_false_denies": sum(
            row["exact_kind_consensus_false_deny"] for row in rows
        ),
        "exact_kind_consensus_changed_decisions": sum(
            row["producer_allowed"]
            != row["exact_kind_consensus_allowed"]
            for row in rows
        ),
    }
    return {
        "producer_model": producer["experiment"]["model"],
        "verifier_model": verifier["experiment"]["model"],
        "metrics": metrics,
        "cases": rows,
    }


def analyze_pair(
    first_path: Path,
    second_path: Path,
    cases_path: Path,
) -> Dict[str, Any]:
    cases = load_jsonl(cases_path)
    dataset_sha256 = sha256_path(cases_path)
    first = _load_report(first_path, dataset_sha256)
    second = _load_report(second_path, dataset_sha256)
    if first["experiment"]["model"] == second["experiment"]["model"]:
        raise ValueError("cross-model analysis requires distinct model IDs")
    directions = [
        _direction(cases, first, second),
        _direction(cases, second, first),
    ]
    return {
        "schema_version": "sri.experiment.cross-model-semantic-guard.v1",
        "experiment": {
            "name": "symmetric-cross-model-deny-only-semantic-guard",
            "evidence_grade": "experimental",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": dataset_sha256,
            "report_paths": [
                str(first_path.resolve()),
                str(second_path.resolve()),
            ],
            "report_sha256": [
                sha256_path(first_path),
                sha256_path(second_path),
            ],
            "combination_rule": (
                "allow only when producer and distinct recorded model-ID "
                "verifier independently yield scope-allowed claim kinds"
            ),
            "missing_response_policy": "fail closed and retain in ITT",
            "limitations": [
                "This is a post-hoc replay over one response per model and case, not a randomized product-effect estimate.",
                "Distinct recorded model IDs and fresh sessions do not prove independent model families, providers, or failure modes.",
                "The corpus is small and hand-authored; it does not estimate deployment error rates.",
                "A second model adds latency and remote-data exposure, which are not measured here.",
            ],
        },
        "directions": directions,
        "metrics": {
            "direction_count": len(directions),
            "baseline_false_allows": sum(
                item["metrics"]["baseline_false_allows"]
                for item in directions
            ),
            "baseline_false_denies": sum(
                item["metrics"]["baseline_false_denies"]
                for item in directions
            ),
            "hybrid_false_allows": sum(
                item["metrics"]["hybrid_false_allows"]
                for item in directions
            ),
            "hybrid_false_denies": sum(
                item["metrics"]["hybrid_false_denies"]
                for item in directions
            ),
            "semantic_disagreements": sum(
                item["metrics"]["semantic_disagreements"]
                for item in directions
            ),
            "exact_kind_consensus_false_allows": sum(
                item["metrics"]["exact_kind_consensus_false_allows"]
                for item in directions
            ),
            "exact_kind_consensus_false_denies": sum(
                item["metrics"]["exact_kind_consensus_false_denies"]
                for item in directions
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("first_report", type=Path)
    parser.add_argument("second_report", type=Path)
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = analyze_pair(
        arguments.first_report,
        arguments.second_report,
        arguments.cases,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "cross-model-semantic-guard",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    for direction in report["directions"]:
        print(
            f"{direction['producer_model']} -> "
            f"{direction['verifier_model']}: "
            f"{json.dumps(direction['metrics'], sort_keys=True)}"
        )
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
