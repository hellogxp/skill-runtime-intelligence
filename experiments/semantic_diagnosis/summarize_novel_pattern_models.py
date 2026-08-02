#!/usr/bin/env python3
"""Summarize cross-model replication of controlled novel-pattern discovery."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sources = [json.loads(args.first.read_text(encoding="utf-8")), json.loads(args.second.read_text(encoding="utf-8"))]
    indexed = [{row["case_id"]: row for row in source["rows"]} for source in sources]
    case_ids = sorted(set(indexed[0]) | set(indexed[1]))
    rows = []
    for case_id in case_ids:
        first, second = indexed[0].get(case_id, {}), indexed[1].get(case_id, {})
        rows.append({"case_id": case_id,
                     "both_completed": first.get("status") == second.get("status") == "completed",
                     "prediction_agreement": first.get("predicted_anomaly") == second.get("predicted_anomaly"),
                     "first_prediction": first.get("predicted_anomaly"), "second_prediction": second.get("predicted_anomaly"),
                     "expected": first.get("expected_anomaly", second.get("expected_anomaly")),
                     "both_support_valid": bool(first.get("support_relation_valid") and second.get("support_relation_valid"))})
    metrics = {"case_count": len(rows), "both_completed": sum(row["both_completed"] for row in rows),
               "prediction_agreement_cases": sum(row["prediction_agreement"] for row in rows),
               "both_support_valid_cases": sum(row["both_support_valid"] for row in rows),
               "disagreement_cases": sum(not row["prediction_agreement"] for row in rows)}
    report = {"schema_version": "sri.experiment.novel-pattern-cross-model-summary.v1",
              "experiment": {"name": "cross-model-rule-external-pattern-replication", "evidence_grade": "Derived",
                 "first_sha256": sha256_path(args.first), "second_sha256": sha256_path(args.second),
                 "limitations": ["Agreement across two models is replication evidence, not proof of a production defect.",
                    "The controlled labels were preregistered by the experiment author, not independently annotated."]},
              "metrics": metrics, "source_metrics": [source["metrics"] for source in sources], "rows": rows,
              "gate": {"name": "two complete model reports with disagreements preserved",
                       "passed": metrics["both_completed"] == metrics["case_count"]}}
    output = write_report(EXPERIMENT_DIR, "novel-pattern-cross-model-summary", report, args.output)
    print(json.dumps({"metrics": metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
