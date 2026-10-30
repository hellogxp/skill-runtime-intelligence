#!/usr/bin/env python3
"""Rescore stored model outputs with the relation-specific citation guard."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.semantic_diagnosis.run_real_failure_model_study import _entailment_valid


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = {item["case_id"]: item for item in json.loads(args.cases.read_text(encoding="utf-8"))["cases"]}
    source = json.loads(args.report.read_text(encoding="utf-8"))
    rows = []
    for row in source.get("model_rows", source.get("rows", [])):
        if row.get("status") != "completed" or row.get("case_id") not in cases:
            rows.append({"case_id": row.get("case_id"), "status": row.get("status"), "citation_entailment_valid": False})
            continue
        findings = row.get("predicted_findings") or []
        rows.append({"case_id": row["case_id"], "status": "completed",
                     "citation_id_valid": bool(row.get("citation_valid")),
                     "citation_entailment_valid": _entailment_valid(findings, cases[row["case_id"]]["evidence"])})
    completed = [row for row in rows if row["status"] == "completed"]
    report = {"schema_version": "sri.experiment.citation-entailment-rescore.v1",
              "experiment": {"name": "stored-model-output-relation-specific-citation-rescore",
                 "evidence_grade": "Derived", "source_report_sha256": sha256_path(args.report),
                 "holdout_sha256": sha256_path(args.cases)},
              "metrics": {"planned": len(rows), "completed": len(completed),
                 "citation_id_valid": sum(row.get("citation_id_valid", False) for row in completed),
                 "citation_entailment_valid": sum(row.get("citation_entailment_valid", False) for row in completed)},
              "rows": rows,
              "gate": {"name": "all completed citations entail asserted relations",
                       "passed": bool(completed) and all(row["citation_entailment_valid"] for row in completed)}}
    output = write_report(EXPERIMENT_DIR, "citation-entailment-rescore", report, args.output)
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
