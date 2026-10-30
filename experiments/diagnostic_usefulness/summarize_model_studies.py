#!/usr/bin/env python3
"""Summarize model-agent studies without hiding per-model heterogeneity."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import sha256_path, write_report
from experiments.diagnostic_usefulness.run_model_study import _metrics


def summarize(paths: List[Path]) -> Dict[str, Any]:
    studies = []
    dataset_digests = set()
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != (
            "sri.experiment.model-agent-usefulness-result.v1"
        ):
            raise ValueError(f"unsupported report schema: {path}")
        dataset_digest = report["experiment"]["dataset_sha256"]
        dataset_digests.add(dataset_digest)
        studies.append(
            {
                "report_path": str(path.resolve()),
                "report_sha256": sha256_path(path),
                "model": report["experiment"]["model"],
                "model_cli_version": report["experiment"][
                    "model_cli_version"
                ],
                "metrics": _metrics(report["trials"]),
                "source_integrity_gate_passed": bool(
                    report.get("gate", {}).get("passed")
                ),
            }
        )
    if len(dataset_digests) != 1:
        raise ValueError("study reports do not use one immutable dataset")
    distinct_models = sorted({study["model"] for study in studies})
    directional_replications = sum(
        study["metrics"][
            "panorama_minus_raw_intention_to_treat_accuracy"
        ]
        > 0
        for study in studies
    )
    integrity_passes = sum(
        study["source_integrity_gate_passed"] for study in studies
    )
    return {
        "schema_version": (
            "sri.experiment.model-agent-usefulness-summary.v1"
        ),
        "experiment": {
            "name": "per-model-diagnostic-usefulness-replication-summary",
            "evidence_grade": "experimental",
            "dataset_sha256": next(iter(dataset_digests)),
            "aggregation_policy": (
                "recompute each model separately; do not pool effect sizes"
            ),
            "limitations": [
                "Recorded model IDs are not independent verification of underlying model-family identity.",
                "The corpus is synthetic and diagnostic-interface specific.",
                "Direction replication does not override a failed response-integrity or causal-safety gate.",
            ],
        },
        "metrics": {
            "study_count": len(studies),
            "distinct_recorded_model_count": len(distinct_models),
            "recorded_models": distinct_models,
            "positive_panorama_direction_count": directional_replications,
            "integrity_gate_pass_count": integrity_passes,
        },
        "studies": studies,
        "gates": {
            "same_dataset": len(dataset_digests) == 1,
            "exploratory_direction_replicated": (
                len(distinct_models) >= 2
                and directional_replications == len(studies)
            ),
            "confirmatory_claim_ready": (
                len(distinct_models) >= 2
                and integrity_passes == len(studies)
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("reports", nargs="+", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = summarize(arguments.reports)
    output = write_report(
        EXPERIMENT_DIR,
        "model-agent-diagnostic-usefulness-summary",
        report,
        arguments.output,
    )
    print(json.dumps({"metrics": report["metrics"], "gates": report["gates"]}, indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
