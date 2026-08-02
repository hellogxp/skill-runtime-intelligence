#!/usr/bin/env python3
"""Remove deterministic candidate labels before independent trace annotation."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


def build_blinded_holdout(source: dict) -> dict:
    cases = [
        {
            "case_id": case["case_id"],
            "source": case.get("source", "deidentified_real_skill_run"),
            "evidence": case["evidence"],
        }
        for case in source["cases"]
    ]
    serialized = json.dumps(cases, sort_keys=True)
    forbidden = ("expected_findings", "label_origin", "production_deterministic")
    passed = bool(cases) and not any(token in serialized for token in forbidden)
    return {
        "schema_version": "sri.experiment.blinded-real-trace-holdout.v1",
        "experiment": {
            "name": "rule-label-blinded-real-trace-annotation-holdout",
            "evidence_grade": "Derived",
            "source_holdout_sha256": None,
            "raw_content_included": False,
            "rule_labels_included": False,
            "limitations": [
                "Cases are deidentified normalized evidence from one local runtime corpus.",
                "Removing deterministic candidate labels prevents direct label leakage but does not make model adjudication human ground truth.",
                "The evidence schema itself exposes lifecycle stages and capability states.",
            ],
        },
        "cases": cases,
        "privacy_and_blinding_audit": {
            "case_count": len(cases),
            "rule_label_tokens_absent": passed,
            "passed": passed,
        },
        "gate": {"name": "non-empty holdout with rule labels removed", "passed": passed},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    source = json.loads(arguments.source.read_text(encoding="utf-8"))
    report = build_blinded_holdout(source)
    report["experiment"]["source_holdout_sha256"] = sha256_path(arguments.source)
    output = write_report(EXPERIMENT_DIR, "blinded-real-trace-holdout", report, arguments.output)
    print(json.dumps({"audit": report["privacy_and_blinding_audit"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
