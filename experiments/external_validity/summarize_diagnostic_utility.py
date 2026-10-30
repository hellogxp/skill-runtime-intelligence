#!/usr/bin/env python3
"""Combine two independent model reports without hiding paired failures."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


VIEWS = ("raw", "raw_semantic", "panorama", "graph_plus_model")


def _paired(rows, left, right):
    indexed = {(row["case_id"], row["view"]): row for row in rows if row.get("status") == "completed"}
    pairs = [(indexed.get((case_id, left)), indexed.get((case_id, right)))
             for case_id in sorted({row["case_id"] for row in rows})]
    usable = [(a, b) for a, b in pairs if a and b]
    return {"pair_count": len(usable),
            "right_wins": sum(not a["exact"] and b["exact"] for a, b in usable),
            "right_losses": sum(a["exact"] and not b["exact"] for a, b in usable),
            "ties": sum(a["exact"] == b["exact"] for a, b in usable),
            "right_minus_left_exact": sum(b["exact"] - a["exact"] for a, b in usable)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    reports = [json.loads(args.first.read_text(encoding="utf-8")), json.loads(args.second.read_text(encoding="utf-8"))]
    model_pairing = []
    indexed = [{(row["case_id"], row["view"]): row for row in report["rows"] if row.get("status") == "completed"} for report in reports]
    keys = sorted(set(indexed[0]) | set(indexed[1]))
    for key in keys:
        first, second = indexed[0].get(key), indexed[1].get(key)
        model_pairing.append({"case_id": key[0], "view": key[1], "both_completed": bool(first and second),
                              "prediction_agreement": bool(first and second and first["predicted"] == second["predicted"]),
                              "both_exact": bool(first and second and first["exact"] and second["exact"]),
                              "both_entailment_valid": bool(first and second and first["citation_entailment_valid"] and second["citation_entailment_valid"])})
    per_model = []
    for report in reports:
        per_model.append({"backend": report["experiment"]["backend"], "model": report["experiment"]["model"],
                          "summary": report["model_summary"],
                          "raw_semantic_vs_raw": _paired(report["rows"], "raw", "raw_semantic"),
                          "panorama_vs_raw_semantic": _paired(report["rows"], "raw_semantic", "panorama"),
                          "panorama_vs_raw": _paired(report["rows"], "raw", "panorama"),
                          "graph_plus_model_vs_panorama": _paired(report["rows"], "panorama", "graph_plus_model")})
    metrics = {"paired_prediction_count": len(model_pairing),
               "both_completed": sum(row["both_completed"] for row in model_pairing),
               "prediction_agreement": sum(row["prediction_agreement"] for row in model_pairing),
               "both_exact": sum(row["both_exact"] for row in model_pairing),
               "both_entailment_valid": sum(row["both_entailment_valid"] for row in model_pairing)}
    report = {"schema_version": "sri.experiment.multirepo-diagnostic-cross-model.v1",
              "experiment": {"name": "paired-cross-model-multirepo-diagnostic-utility", "evidence_grade": "Derived",
                 "first_sha256": sha256_path(args.first), "second_sha256": sha256_path(args.second),
                 "limitations": ["Two models do not form a majority and share the same controlled gold.",
                    "Paired wins and losses are descriptive unless a separately preregistered inferential test is added.",
                    "Cross-model agreement never promotes an Inferred diagnosis to Observed or Derived."]},
              "per_model": per_model, "metrics": metrics, "rows": model_pairing,
              "gate": {"name": "both reports complete for every case-view pair",
                       "passed": metrics["both_completed"] == metrics["paired_prediction_count"]}}
    output = write_report(EXPERIMENT_DIR, "multirepo-diagnostic-cross-model", report, args.output)
    print(json.dumps({"per_model": per_model, "metrics": metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
