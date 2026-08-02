#!/usr/bin/env python3
"""Preserve agreements and disagreements between two independent model reports."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.semantic_diagnosis.run_real_failure_model_study import _citation_entails, _signature


def _rows(report):
    return report.get("model_rows", report.get("rows", []))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = {case["case_id"]: case for case in json.loads(args.cases.read_text(encoding="utf-8"))["cases"]}
    reports = [json.loads(args.first.read_text(encoding="utf-8")), json.loads(args.second.read_text(encoding="utf-8"))]
    indexed = [{row.get("case_id"): row for row in _rows(report)} for report in reports]
    rows = []
    for case_id in sorted(cases):
        pair = [index.get(case_id, {}) for index in indexed]
        completed = all(row.get("status") == "completed" for row in pair)
        findings = [row.get("predicted_findings") or [] for row in pair]
        signatures = [{_signature(item) for item in group} for group in findings]
        entailed = [{_signature(item) for item in group if _citation_entails(item, cases[case_id]["evidence"])} for group in findings]
        rows.append({"case_id": case_id, "both_completed": completed,
                     "prediction_agreement": completed and signatures[0] == signatures[1],
                     "entailed_agreement": completed and entailed[0] == entailed[1],
                     "first_predicted": sorted(signatures[0]), "second_predicted": sorted(signatures[1]),
                     "first_entailed": sorted(entailed[0]), "second_entailed": sorted(entailed[1]),
                     "consensus_entailed": sorted(entailed[0] & entailed[1]),
                     "disagreement_preserved": sorted(signatures[0] ^ signatures[1])})
    metrics = {"case_count": len(rows), "both_completed": sum(row["both_completed"] for row in rows),
               "prediction_agreement_cases": sum(row["prediction_agreement"] for row in rows),
               "entailed_agreement_cases": sum(row["entailed_agreement"] for row in rows),
               "cases_with_any_consensus_entailed_finding": sum(bool(row["consensus_entailed"]) for row in rows),
               "disagreement_cases": sum(bool(row["disagreement_preserved"]) for row in rows)}
    report = {"schema_version": "sri.experiment.double-model-adjudication.v1",
              "experiment": {"name": "independent-model-double-adjudication-with-disagreement-preservation",
                 "evidence_grade": "Derived", "first_report_sha256": sha256_path(args.first),
                 "second_report_sha256": sha256_path(args.second), "holdout_sha256": sha256_path(args.cases),
                 "limitations": ["Two models cannot form a majority; disagreement is preserved rather than resolved.",
                    "Consensus requires independently citation-entailed finding signatures, not just matching labels.",
                    "Expected labels remain deterministic production candidates, not human gold labels."]},
              "metrics": metrics, "rows": rows,
              "gate": {"name": "both independent reports complete with explicit disagreement ledger",
                       "passed": metrics["both_completed"] == metrics["case_count"]}}
    output = write_report(EXPERIMENT_DIR, "double-model-adjudication", report, args.output)
    print(json.dumps({"metrics": metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
