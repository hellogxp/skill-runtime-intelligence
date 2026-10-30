#!/usr/bin/env python3
"""Summarize cross-model guard accuracy and operational cost."""

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.run_claim_output_mode_study import (
    _prompt,
)


def _percentile(values: List[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _structured_rows(report: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        row["case_id"]: row
        for row in report["trials"]
        if row["mode"] == "structured" and row["status"] == "completed"
    }


def _usage(rows: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    keys = ("input", "output", "reasoning", "total")
    return {
        key: sum(int(row.get("usage", {}).get(key, 0)) for row in rows.values())
        for key in keys
    }


def _study(path: Path) -> Dict[str, Any]:
    guard = json.loads(path.read_text(encoding="utf-8"))
    if guard.get("schema_version") != (
        "sri.experiment.cross-model-semantic-guard.v1"
    ):
        raise ValueError(f"unsupported cross-model report: {path}")
    cases_path = Path(guard["experiment"]["dataset_path"])
    cases = load_jsonl(cases_path)
    report_paths = [
        Path(item) for item in guard["experiment"]["report_paths"]
    ]
    model_reports = [
        json.loads(item.read_text(encoding="utf-8"))
        for item in report_paths
    ]
    rows = [_structured_rows(report) for report in model_reports]
    case_ids = [case["case_id"] for case in cases]
    if any(set(item) != set(case_ids) for item in rows):
        raise ValueError(f"incomplete structured rows for cost audit: {path}")
    paired_latencies = [
        [item[case_id]["elapsed_ms"] for item in rows]
        for case_id in case_ids
    ]
    directions = []
    for producer_index, verifier_index in ((0, 1), (1, 0)):
        producer = rows[producer_index]
        verifier = rows[verifier_index]
        producer_latency = [
            producer[case_id]["elapsed_ms"] for case_id in case_ids
        ]
        verifier_latency = [
            verifier[case_id]["elapsed_ms"] for case_id in case_ids
        ]
        serial = [
            producer[case_id]["elapsed_ms"]
            + verifier[case_id]["elapsed_ms"]
            for case_id in case_ids
        ]
        parallel = [
            max(
                producer[case_id]["elapsed_ms"],
                verifier[case_id]["elapsed_ms"],
            )
            for case_id in case_ids
        ]
        parallel_increment = [
            max(0.0, parallel[index] - producer_latency[index])
            for index in range(len(case_ids))
        ]
        directions.append(
            {
                "producer_model": model_reports[producer_index][
                    "experiment"
                ]["model"],
                "verifier_model": model_reports[verifier_index][
                    "experiment"
                ]["model"],
                "observed_producer_latency_p50_ms": statistics.median(
                    producer_latency
                ),
                "observed_verifier_latency_p50_ms": statistics.median(
                    verifier_latency
                ),
                "computed_serial_path_p50_ms": statistics.median(serial),
                "computed_parallel_path_p50_ms": statistics.median(parallel),
                "computed_parallel_increment_p50_ms": statistics.median(
                    parallel_increment
                ),
                "computed_parallel_increment_p95_ms": _percentile(
                    parallel_increment, 0.95
                ),
            }
        )
    usage = [_usage(item) for item in rows]
    prompt_bytes_per_model = sum(
        len(_prompt(case, "structured").encode("utf-8"))
        for case in cases
    )
    return {
        "cross_model_report_path": str(path.resolve()),
        "cross_model_report_sha256": sha256_path(path),
        "dataset_path": str(cases_path.resolve()),
        "dataset_sha256": sha256_path(cases_path),
        "case_count": len(cases),
        "recorded_models": [
            report["experiment"]["model"] for report in model_reports
        ],
        "structured_call_count": sum(len(item) for item in rows),
        "baseline_single_model_call_count": len(cases),
        "additional_verifier_call_count": len(cases),
        "usage": {
            "combined": {
                key: sum(item[key] for item in usage)
                for key in ("input", "output", "reasoning", "total")
            },
            "by_model": usage,
        },
        "minimum_claim_prompt_bytes": {
            "one_model": prompt_bytes_per_model,
            "two_models": prompt_bytes_per_model * 2,
            "additional_verifier": prompt_bytes_per_model,
        },
        "observed_single_call_latency_p50_ms": statistics.median(
            latency
            for pair in paired_latencies
            for latency in pair
        ),
        "directions": directions,
        "guard_metrics": guard["metrics"],
    }


def summarize(paths: List[Path]) -> Dict[str, Any]:
    studies = [_study(path) for path in paths]
    combined_usage = {
        key: sum(study["usage"]["combined"][key] for study in studies)
        for key in ("input", "output", "reasoning", "total")
    }
    usage_by_model: Dict[str, Dict[str, int]] = {}
    for study in studies:
        for model, usage in zip(
            study["recorded_models"], study["usage"]["by_model"]
        ):
            aggregate = usage_by_model.setdefault(
                model,
                {key: 0 for key in ("input", "output", "reasoning", "total")},
            )
            for key, value in usage.items():
                aggregate[key] += value
    return {
        "schema_version": "sri.experiment.cross-model-guard-summary.v1",
        "experiment": {
            "name": "cross-model-semantic-guard-accuracy-cost-summary",
            "evidence_grade": "derived",
            "aggregation_policy": (
                "retain per-corpus and per-direction latency; aggregate "
                "only counts, usage, and safety events"
            ),
            "limitations": [
                "All latency values are from concurrent multi-worker experiment runs, not controlled single-request production traffic.",
                "Serial and parallel path latency values are arithmetic replays over observed calls; those schedules were not directly executed.",
                "Reported token usage includes provider and CLI context beyond the visible claim prompt.",
                "Prompt bytes are reconstructed minimum outbound payload sizes, not network-capture measurements.",
                "The corpora are hand-authored and reuse two recorded model IDs.",
            ],
        },
        "metrics": {
            "study_count": len(studies),
            "unique_case_count": sum(
                study["case_count"] for study in studies
            ),
            "structured_call_count": sum(
                study["structured_call_count"] for study in studies
            ),
            "additional_verifier_call_count": sum(
                study["additional_verifier_call_count"]
                for study in studies
            ),
            "combined_usage": combined_usage,
            "usage_by_model": usage_by_model,
            "minimum_additional_prompt_bytes": sum(
                study["minimum_claim_prompt_bytes"][
                    "additional_verifier"
                ]
                for study in studies
            ),
            "baseline_false_allows": sum(
                study["guard_metrics"]["baseline_false_allows"]
                for study in studies
            ),
            "baseline_false_denies": sum(
                study["guard_metrics"]["baseline_false_denies"]
                for study in studies
            ),
            "hybrid_false_allows": sum(
                study["guard_metrics"]["hybrid_false_allows"]
                for study in studies
            ),
            "hybrid_false_denies": sum(
                study["guard_metrics"]["hybrid_false_denies"]
                for study in studies
            ),
            "semantic_disagreements": sum(
                study["guard_metrics"]["semantic_disagreements"]
                for study in studies
            ),
            "exact_kind_consensus_false_denies": sum(
                study["guard_metrics"].get(
                    "exact_kind_consensus_false_denies", 0
                )
                for study in studies
            ),
        },
        "studies": studies,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = summarize(arguments.reports)
    output = write_report(
        EXPERIMENT_DIR,
        "cross-model-guard-summary",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
