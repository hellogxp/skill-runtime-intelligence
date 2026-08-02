#!/usr/bin/env python3
"""Summarize claim-output mode studies without pooling model effects."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


def summarize(paths: List[Path]) -> Dict[str, Any]:
    studies = []
    dataset_digests = set()
    for path in paths:
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != (
            "sri.experiment.claim-output-mode-study.v1"
        ):
            raise ValueError(f"unsupported report schema: {path}")
        dataset_digests.add(report["experiment"]["dataset_sha256"])
        studies.append(
            {
                "report_path": str(path.resolve()),
                "report_sha256": sha256_path(path),
                "model": report["experiment"]["model"],
                "metrics": report["metrics"],
                "gate_passed": bool(report["gate"]["passed"]),
            }
        )
    if len(dataset_digests) != 1:
        raise ValueError("reports do not share one immutable dataset")
    structured_advantages = sum(
        study["metrics"]["structured_minus_free_text_kind_accuracy"] > 0
        for study in studies
    )
    structured_false_allows = sum(
        study["metrics"]["by_mode"]["structured"]["false_allows"]
        for study in studies
    )
    free_text_false_denies = sum(
        study["metrics"]["by_mode"]["free_text"]["false_denies"]
        for study in studies
    )
    model_guard_disagreements = sum(
        study["metrics"]["by_mode"]["structured"][
            "model_guard_disagreements"
        ]
        for study in studies
    )
    return {
        "schema_version": "sri.experiment.claim-output-mode-summary.v1",
        "experiment": {
            "name": "per-model-claim-output-mode-summary",
            "evidence_grade": "experimental",
            "dataset_sha256": next(iter(dataset_digests)),
            "aggregation_policy": (
                "retain per-model metrics; aggregate only safety event counts"
            ),
            "limitations": [
                "The same small hand-authored challenge is reused for both models.",
                "Recorded model IDs do not independently verify underlying model-family identity.",
                "No pooled effect size or population inference is reported.",
            ],
        },
        "metrics": {
            "study_count": len(studies),
            "distinct_recorded_model_count": len(
                {study["model"] for study in studies}
            ),
            "structured_kind_advantage_count": structured_advantages,
            "structured_false_allow_count": structured_false_allows,
            "free_text_false_deny_count": free_text_false_denies,
            "model_guard_disagreement_count": model_guard_disagreements,
        },
        "studies": studies,
        "gates": {
            "same_dataset": len(dataset_digests) == 1,
            "structured_kind_advantage_replicated": (
                structured_advantages == len(studies)
            ),
            "confirmatory_safety_ready": structured_false_allows == 0,
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
        "claim-output-mode-summary",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {"metrics": report["metrics"], "gates": report["gates"]},
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
