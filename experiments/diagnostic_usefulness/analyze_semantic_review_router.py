#!/usr/bin/env python3
"""Replay a cheap local-conflict router for cross-model semantic review."""

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
from experiments.diagnostic_usefulness.run_claim_output_mode_study import (
    _prompt,
)
from skill_runtime_intelligence.diagnostics import validate_causal_claim


def _rows(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["case_id"]: row
        for row in report["trials"]
        if row["mode"] == "structured"
    }


def _study(path: Path) -> Dict[str, Any]:
    cross = json.loads(path.read_text(encoding="utf-8"))
    if cross.get("schema_version") != (
        "sri.experiment.cross-model-semantic-guard.v1"
    ):
        raise ValueError(f"unsupported cross-model report: {path}")
    cases_path = Path(cross["experiment"]["dataset_path"])
    cases = load_jsonl(cases_path)
    reports = [
        json.loads(Path(item).read_text(encoding="utf-8"))
        for item in cross["experiment"]["report_paths"]
    ]
    report_rows = [_rows(report) for report in reports]
    directions = []
    for producer_index, verifier_index in ((0, 1), (1, 0)):
        producer_rows = report_rows[producer_index]
        verifier_rows = report_rows[verifier_index]
        rows = []
        for case in cases:
            producer = producer_rows.get(case["case_id"])
            verifier = verifier_rows.get(case["case_id"])
            producer_completed = bool(
                producer and producer["status"] == "completed"
            )
            verifier_completed = bool(
                verifier and verifier["status"] == "completed"
            )
            producer_allowed = bool(
                producer_completed and producer["predicted_allowed"]
            )
            local = classify_claim_fail_closed_v3(case["text"])
            review_invoked = bool(
                producer_allowed
                and local["claim_kind"] != "unknown"
                and local["claim_kind"]
                != producer["predicted_claim_kind"]
            )
            verifier_allowed = bool(
                verifier_completed
                and validate_causal_claim(
                    case["causal_scope"],
                    verifier["predicted_claim_kind"],
                )["allowed"]
            )
            routed_allowed = bool(
                producer_allowed
                and (not review_invoked or verifier_allowed)
            )
            usage = verifier.get("usage", {}) if verifier_completed else {}
            rows.append(
                {
                    "case_id": case["case_id"],
                    "expected_allowed": case["expected_allowed"],
                    "producer_claim_kind": (
                        producer.get("predicted_claim_kind")
                        if producer_completed
                        else "unavailable"
                    ),
                    "producer_allowed": producer_allowed,
                    "local_router_claim_kind": local["claim_kind"],
                    "review_invoked": review_invoked,
                    "verifier_completed": verifier_completed,
                    "verifier_claim_kind": (
                        verifier.get("predicted_claim_kind")
                        if verifier_completed
                        else "unavailable"
                    ),
                    "routed_allowed": routed_allowed,
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
                    "review_input_tokens": (
                        int(usage.get("input", 0)) if review_invoked else 0
                    ),
                    "review_total_tokens": (
                        int(usage.get("total", 0)) if review_invoked else 0
                    ),
                    "review_prompt_bytes": (
                        len(_prompt(case, "structured").encode("utf-8"))
                        if review_invoked
                        else 0
                    ),
                }
            )
        metrics = {
            "case_count": len(rows),
            "review_invocations": sum(
                row["review_invoked"] for row in rows
            ),
            "review_rate": (
                sum(row["review_invoked"] for row in rows) / len(rows)
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
            "captured_false_allows": sum(
                row["baseline_false_allow"]
                and not row["routed_false_allow"]
                for row in rows
            ),
            "changed_decisions": sum(
                row["producer_allowed"] != row["routed_allowed"]
                for row in rows
            ),
            "review_input_tokens": sum(
                row["review_input_tokens"] for row in rows
            ),
            "review_total_tokens": sum(
                row["review_total_tokens"] for row in rows
            ),
            "review_prompt_bytes": sum(
                row["review_prompt_bytes"] for row in rows
            ),
        }
        directions.append(
            {
                "producer_model": reports[producer_index]["experiment"][
                    "model"
                ],
                "verifier_model": reports[verifier_index]["experiment"][
                    "model"
                ],
                "metrics": metrics,
                "cases": rows,
            }
        )
    return {
        "cross_model_report_path": str(path.resolve()),
        "cross_model_report_sha256": sha256_path(path),
        "dataset_path": str(cases_path.resolve()),
        "dataset_sha256": sha256_path(cases_path),
        "directions": directions,
    }


def analyze(paths: List[Path]) -> Dict[str, Any]:
    studies = [_study(path) for path in paths]
    directions = [
        direction
        for study in studies
        for direction in study["directions"]
    ]
    return {
        "schema_version": "sri.experiment.semantic-review-router.v1",
        "experiment": {
            "name": "frozen-local-conflict-to-cross-model-review-router",
            "evidence_grade": "derived",
            "routing_policy": (
                "invoke the second model only when producer scope allows, "
                "frozen-v3 returns a known kind, and kinds disagree"
            ),
            "decision_policy": (
                "if invoked, intersect producer and verifier scope decisions; "
                "the local classifier never directly changes authorization"
            ),
            "limitations": [
                "The router inherits v3 rules tuned on the first challenge.",
                "This is a post-hoc replay and does not measure live queue latency or failure recovery.",
                "The hand-authored corpora and two recorded model IDs do not estimate deployment performance.",
                "Review token counts come from already completed calls; uninvoked calls were not actually avoided in the source experiments.",
            ],
        },
        "metrics": {
            "study_count": len(studies),
            "direction_count": len(directions),
            "directional_case_count": sum(
                item["metrics"]["case_count"] for item in directions
            ),
            "review_invocations": sum(
                item["metrics"]["review_invocations"]
                for item in directions
            ),
            "review_rate": (
                sum(
                    item["metrics"]["review_invocations"]
                    for item in directions
                )
                / sum(
                    item["metrics"]["case_count"] for item in directions
                )
                if directions
                else 0.0
            ),
            "baseline_false_allows": sum(
                item["metrics"]["baseline_false_allows"]
                for item in directions
            ),
            "baseline_false_denies": sum(
                item["metrics"]["baseline_false_denies"]
                for item in directions
            ),
            "routed_false_allows": sum(
                item["metrics"]["routed_false_allows"]
                for item in directions
            ),
            "routed_false_denies": sum(
                item["metrics"]["routed_false_denies"]
                for item in directions
            ),
            "captured_false_allows": sum(
                item["metrics"]["captured_false_allows"]
                for item in directions
            ),
            "review_input_tokens": sum(
                item["metrics"]["review_input_tokens"]
                for item in directions
            ),
            "review_total_tokens": sum(
                item["metrics"]["review_total_tokens"]
                for item in directions
            ),
            "review_prompt_bytes": sum(
                item["metrics"]["review_prompt_bytes"]
                for item in directions
            ),
        },
        "studies": studies,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = analyze(arguments.reports)
    output = write_report(
        EXPERIMENT_DIR,
        "semantic-review-router",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
