#!/usr/bin/env python3
"""Describe model diagnostic failures by gold finding family and stage."""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report


def _case_metadata(cases: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    metadata = {}
    for case in cases:
        findings = case.get("expected_findings") or []
        if not findings:
            continue
        first = findings[0]
        metadata[case["case_id"]] = {
            "finding_family": first["code"],
            "gold_stage": first["stage"],
        }
    return metadata


def _empty_bucket() -> Dict[str, int]:
    return {
        "planned": 0,
        "valid": 0,
        "correct": 0,
        "parse_or_execution_errors": 0,
        "unsupported_causal_claims": 0,
    }


def _bucket_rows(
    trials: Iterable[Dict[str, Any]],
    metadata: Dict[str, Dict[str, str]],
    dimension: str,
) -> Dict[str, Dict[str, Dict[str, Any]]]:
    buckets = defaultdict(lambda: defaultdict(_empty_bucket))
    for trial in trials:
        case = metadata[trial["case_id"]]
        dimension_value = case[dimension]
        bucket = buckets[trial["condition"]][dimension_value]
        bucket["planned"] += 1
        if trial["status"] == "completed":
            bucket["valid"] += 1
            bucket["correct"] += int(bool(trial["correct"]))
            bucket["unsupported_causal_claims"] += int(
                bool(trial["unsupported_causal_claim"])
            )
        else:
            bucket["parse_or_execution_errors"] += 1
    result = {}
    for condition, values in sorted(buckets.items()):
        result[condition] = {}
        for value, bucket in sorted(values.items()):
            result[condition][value] = {
                **bucket,
                "intention_to_treat_accuracy": (
                    bucket["correct"] / bucket["planned"]
                    if bucket["planned"]
                    else 0.0
                ),
            }
    return result


def analyze(paths: List[Path], cases_path: Path) -> Dict[str, Any]:
    cases = load_jsonl(cases_path)
    metadata = _case_metadata(cases)
    reports = []
    dataset_digests = set()
    case_errors = defaultdict(
        lambda: {
            "planned": 0,
            "correct": 0,
            "invalid": 0,
            "unsupported_causal_claims": 0,
        }
    )
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != (
            "sri.experiment.model-agent-usefulness-result.v1"
        ):
            raise ValueError(f"unsupported report schema: {path}")
        dataset_digests.add(report["experiment"]["dataset_sha256"])
        unknown_cases = {
            trial["case_id"] for trial in report["trials"]
        } - metadata.keys()
        if unknown_cases:
            raise ValueError(
                f"trials missing case metadata: {sorted(unknown_cases)}"
            )
        for trial in report["trials"]:
            key = f"{trial['condition']}:{trial['case_id']}"
            case_errors[key]["planned"] += 1
            if trial["status"] == "completed":
                case_errors[key]["correct"] += int(bool(trial["correct"]))
                case_errors[key]["unsupported_causal_claims"] += int(
                    bool(trial["unsupported_causal_claim"])
                )
            else:
                case_errors[key]["invalid"] += 1
        reports.append(
            {
                "report_path": str(path.resolve()),
                "report_sha256": sha256_path(path),
                "model": report["experiment"]["model"],
                "by_finding_family": _bucket_rows(
                    report["trials"], metadata, "finding_family"
                ),
                "by_gold_stage": _bucket_rows(
                    report["trials"], metadata, "gold_stage"
                ),
            }
        )
    if len(dataset_digests) != 1:
        raise ValueError("reports do not share one immutable dataset")
    difficult_cells = []
    for key, counts in sorted(case_errors.items()):
        condition, case_id = key.split(":", 1)
        if (
            counts["correct"] < counts["planned"]
            or counts["unsupported_causal_claims"]
        ):
            difficult_cells.append(
                {
                    "case_id": case_id,
                    "condition": condition,
                    **metadata[case_id],
                    **counts,
                    "intention_to_treat_accuracy": (
                        counts["correct"] / counts["planned"]
                    ),
                }
            )
    return {
        "schema_version": (
            "sri.experiment.model-agent-failure-mode-analysis.v1"
        ),
        "experiment": {
            "name": "post-hoc-model-diagnostic-failure-mode-analysis",
            "evidence_grade": "derived",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": next(iter(dataset_digests)),
            "analysis_policy": (
                "invalid responses count as incorrect; report model strata "
                "separately; no causal or population-generalization claim"
            ),
            "limitations": [
                "Finding families reuse deterministic corpus gold labels and were not independently annotated for this analysis.",
                "The analysis is post-hoc and descriptive.",
                "Trials from repeated sessions and cases are not independent population samples.",
            ],
        },
        "metrics": {
            "report_count": len(reports),
            "model_count": len({report["model"] for report in reports}),
            "difficult_condition_case_cell_count": len(difficult_cells),
        },
        "reports": reports,
        "difficult_condition_case_cells": difficult_cells,
        "gate": {
            "name": "failure-mode audit integrity",
            "passed": len(dataset_digests) == 1,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
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
    report = analyze(arguments.reports, arguments.cases)
    output = write_report(
        EXPERIMENT_DIR,
        "model-agent-diagnostic-failure-modes",
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
