#!/usr/bin/env python3
"""Aggregate prospective fragility studies with readiness gates."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


MIN_HOLDOUTS = 3
MIN_CASES = 48
MIN_BASELINE_FALSE_ALLOWS = 5
MIN_SHADOW_CASES = 12


def _group(rows: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
    groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[field])].append(row)
    return {
        key: {
            "case_count": len(items),
            "selected_count": sum(item["selected"] for item in items),
            "baseline_false_allows": sum(
                item["baseline_false_allow"] for item in items
            ),
            "routed_false_allows": sum(
                item["routed_false_allow"] for item in items
            ),
            "routed_false_denies": sum(
                item["routed_false_deny"] for item in items
            ),
            "random_shadow_count": sum(
                item["random_shadow_selected"] for item in items
            ),
            "shadow_guard_errors": sum(
                item["shadow_guard_error"] for item in items
            ),
        }
        for key, items in sorted(groups.items())
    }


def summarize(paths: List[Path]) -> Dict[str, Any]:
    studies = []
    rows = []
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != (
            "sri.experiment.prospective-fragility-study.v1"
        ):
            raise ValueError(f"unsupported report: {path}")
        studies.append(
            {
                "report_path": str(path.resolve()),
                "report_sha256": sha256_path(path),
                "dataset_sha256": report["experiment"]["dataset_sha256"],
                "metrics": report["metrics"],
            }
        )
        rows.extend(report["cases"])
    metrics = {
        "holdout_count": len(studies),
        "case_count": len(rows),
        "selected_count": sum(item["selected"] for item in rows),
        "random_shadow_count": sum(
            item["random_shadow_selected"] for item in rows
        ),
        "baseline_false_allows": sum(
            item["baseline_false_allow"] for item in rows
        ),
        "baseline_false_denies": sum(
            item["baseline_false_deny"] for item in rows
        ),
        "captured_false_allows": sum(
            item["baseline_false_allow"]
            and not item["routed_false_allow"]
            for item in rows
        ),
        "missed_false_allows": sum(
            item["baseline_false_allow"] and item["routed_false_allow"]
            for item in rows
        ),
        "routed_false_allows": sum(
            item["routed_false_allow"] for item in rows
        ),
        "routed_false_denies": sum(
            item["routed_false_deny"] for item in rows
        ),
        "shadow_semantic_disagreements": sum(
            item["shadow_semantic_disagreement"] for item in rows
        ),
        "shadow_guard_errors": sum(
            item["shadow_guard_error"] for item in rows
        ),
        "selected_input_tokens": sum(
            study["metrics"]["selected_input_tokens"]
            for study in studies
        ),
        "shadow_input_tokens": sum(
            study["metrics"]["shadow_input_tokens"]
            for study in studies
        ),
    }
    readiness = {
        "minimum_holdouts": metrics["holdout_count"] >= MIN_HOLDOUTS,
        "minimum_cases": metrics["case_count"] >= MIN_CASES,
        "minimum_baseline_false_allows": (
            metrics["baseline_false_allows"]
            >= MIN_BASELINE_FALSE_ALLOWS
        ),
        "minimum_shadow_cases": (
            metrics["random_shadow_count"] >= MIN_SHADOW_CASES
        ),
    }
    return {
        "schema_version": (
            "sri.experiment.prospective-fragility-summary.v1"
        ),
        "experiment": {
            "name": "prospective-fragility-replication-summary",
            "evidence_grade": "experimental",
            "promotion_minimums": {
                "holdouts": MIN_HOLDOUTS,
                "cases": MIN_CASES,
                "baseline_false_allows": MIN_BASELINE_FALSE_ALLOWS,
                "random_shadow_cases": MIN_SHADOW_CASES,
            },
            "limitations": [
                "Minimums are product discussion gates, not statistical power guarantees.",
                "All corpora are hand-authored and use one producer/verifier model-ID pair.",
                "Sparse errors preclude stable rate or subgroup estimates.",
            ],
        },
        "metrics": metrics,
        "by_scope": _group(rows, "causal_scope"),
        "by_expected_claim_kind": _group(rows, "expected_claim_kind"),
        "studies": studies,
        "readiness": readiness,
        "promotion_ready": all(readiness.values()),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = summarize(arguments.reports)
    output = write_report(
        EXPERIMENT_DIR,
        "prospective-fragility-summary",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "readiness": report["readiness"],
                "promotion_ready": report["promotion_ready"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
