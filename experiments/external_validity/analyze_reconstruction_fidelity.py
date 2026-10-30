#!/usr/bin/env python3
"""Score adapter reconstruction against executed fault-manifest boundaries."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


STAGES = ("instructions", "resources", "execution", "artifacts", "outcome")
FAILURE_MODES = {"instructions_failure", "resource_missing", "execution_failure", "artifact_corruption"}


def _telemetry_boundary(row):
    failed = [item for item in row.get("collector_evidence", {}).get("event_signatures", [])
              if item.get("status") == "failed" and item.get("stage") in STAGES]
    return min((item["stage"] for item in failed), key=STAGES.index) if failed else "none"


def analyze(rows):
    scored = []
    for row in rows:
        predicted = _telemetry_boundary(row)
        is_failure = row["fault_mode"] in FAILURE_MODES
        scored.append({"agent": row["agent"], "repo_key": row["repo_key"], "fault_mode": row["fault_mode"],
                       "gold_boundary": row["gold_boundary"], "telemetry_boundary": predicted,
                       "failure_condition": is_failure,
                       "failure_detected": is_failure and predicted != "none",
                       "boundary_exact": is_failure and predicted == row["gold_boundary"],
                       "clean_false_positive": row["fault_mode"] == "clean" and predicted != "none",
                       "skill_run_present": row.get("collector_evidence", {}).get("skill_run_count", 0) > 0,
                       "exact_session_match": row.get("collector_evidence", {}).get("session_match_count") == 1})
    per_agent = {}
    for agent in sorted({row["agent"] for row in scored}):
        selected = [row for row in scored if row["agent"] == agent]
        failures = [row for row in selected if row["failure_condition"]]
        clean = [row for row in selected if row["fault_mode"] == "clean"]
        per_agent[agent] = {"sessions": len(selected), "exact_session_matches": sum(row["exact_session_match"] for row in selected),
                            "skill_run_coverage": sum(row["skill_run_present"] for row in selected) / len(selected),
                            "failure_conditions": len(failures),
                            "failure_detection_recall": sum(row["failure_detected"] for row in failures) / len(failures),
                            "exact_boundary_rate": sum(row["boundary_exact"] for row in failures) / len(failures),
                            "clean_conditions": len(clean),
                            "clean_false_positive_rate": sum(row["clean_false_positive"] for row in clean) / len(clean)}
    return scored, per_agent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source_report.read_text(encoding="utf-8"))
    rows, per_agent = analyze(source["rows"])
    report = {"schema_version": "sri.experiment.multirepo-reconstruction-fidelity.v1",
              "experiment": {"name": "adapter-reconstruction-vs-executed-fault-boundary", "evidence_grade": "Experimental",
                 "source_report_sha256": sha256_path(args.source_report),
                 "limitations": ["Failure ground truth is controlled and executed over real repository snapshots.",
                    "Any failed tool event in a session is counted; current telemetry cannot prove it came from the injected probe.",
                    "Outcome-unverified and verifier-conflict cases are excluded from lifecycle failure recall because they require external outcome evidence."]},
              "per_agent": per_agent, "rows": rows,
              "gate": {"name": "all source sessions exactly correlated", "passed": all(row["exact_session_match"] for row in rows)}}
    output = write_report(EXPERIMENT_DIR, "multirepo-reconstruction-fidelity", report, args.output)
    print(json.dumps({"per_agent": per_agent, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
