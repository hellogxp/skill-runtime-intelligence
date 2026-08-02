#!/usr/bin/env python3
"""Build paired raw/Panorama/graph views from the executed multi-repo matrix."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


STAGES = ("instructions", "resources", "execution", "artifacts", "outcome")


def _gold(row):
    mode = row["fault_mode"]
    status = {
        "clean": "verified_success",
        "instructions_failure": "observed_failure",
        "resource_missing": "observed_failure",
        "execution_failure": "observed_failure",
        "artifact_corruption": "observed_failure",
        "outcome_unverified": "outcome_unverified",
        "verifier_conflict": "verifier_conflict",
    }[mode]
    return {"boundary": row["gold_boundary"], "diagnosis_status": status}


def _raw_evidence(row):
    records = []
    for index, item in enumerate(row["gold_trace"], 1):
        records.append({"evidence_id": f"R{index:02d}", "native_type": "probe.step",
                        "ordinal": index, "native_status_code": {"observed": 0, "failed": 1, "not_observed": 2, "not_verified": 3}[item["status"]]})
    records.extend([
        {"evidence_id": "R06", "native_type": "agent.result", "value": row["gold_reported_status"]},
        {"evidence_id": "R07", "native_type": "external.check", "value": row["gold_verifier_status"]},
    ])
    for index, signature in enumerate(row.get("collector_evidence", {}).get("event_signatures", []), 8):
        records.append({"evidence_id": f"R{index:02d}", "native_type": signature["event_type"],
                        "native_status": signature["status"], "count": signature["count"]})
    return records


def _panorama_evidence(row):
    records = [{"evidence_id": f"P{index:02d}", "kind": "lifecycle_stage", "stage": item["stage"],
                "status": item["status"], "evidence_grade": item["grade"]}
               for index, item in enumerate(row["gold_trace"], 1)]
    records.extend([
        {"evidence_id": "P06", "kind": "reported_outcome", "status": row["gold_reported_status"], "evidence_grade": "experimental"},
        {"evidence_id": "P07", "kind": "external_verifier", "status": row["gold_verifier_status"], "evidence_grade": "experimental"},
    ])
    return records


def _graph_candidate(panorama):
    stages = [item for item in panorama if item["kind"] == "lifecycle_stage"]
    failed = next((item for item in stages if item["status"] in {"failed", "not_verified"}), None)
    reported = next(item for item in panorama if item["kind"] == "reported_outcome")
    verifier = next(item for item in panorama if item["kind"] == "external_verifier")
    if failed and failed["status"] == "not_verified":
        status = "outcome_unverified"
        citations = [failed["evidence_id"], reported["evidence_id"], verifier["evidence_id"]]
    elif failed and failed["stage"] == "outcome" and reported["status"] == "success" and verifier["status"] == "failed":
        status = "verifier_conflict"
        citations = [failed["evidence_id"], reported["evidence_id"], verifier["evidence_id"]]
    elif failed:
        status = "observed_failure"
        citations = [failed["evidence_id"]]
    else:
        status = "verified_success"
        citations = [reported["evidence_id"], verifier["evidence_id"]]
    return {"boundary": failed["stage"] if failed else "none", "diagnosis_status": status,
            "citations": citations, "evidence_grade": "experimental"}


def build_holdout(source):
    cases = []
    for row in source["rows"]:
        if not row.get("gold_trace"):
            continue
        raw = _raw_evidence(row)
        panorama = _panorama_evidence(row)
        graph = _graph_candidate(panorama)
        cases.append({"case_id": f"{row['agent']}-{row['repo_key']}-{row['fault_mode']}",
                      "agent": row["agent"], "repo_key": row["repo_key"], "skill_id": row["skill_id"],
                      "fault_mode": row["fault_mode"], "gold": _gold(row),
                      "agent_attempt_status": row["status"],
                      "agent_response_verified": bool(row.get("outcome_verified")),
                      "raw_evidence": raw, "panorama_evidence": panorama, "graph_candidate": graph,
                      "label_origin": "executed_fault_manifest_plus_deterministic_oracle",
                      "source_revision": row["source_revision"], "source_digest": row["source_digest"]})
    return cases


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-report", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    source = json.loads(args.source_report.read_text(encoding="utf-8"))
    cases = build_holdout(source)
    expected = len(source["experiment"]["agents"]) * len(source["experiment"]["source_manifest"]) * len(source["experiment"]["fault_modes"]) * source["experiment"]["repetitions"]
    report = {"schema_version": "sri.experiment.multirepo-diagnostic-holdout.v1",
              "experiment": {"name": "deidentified-executed-multirepo-diagnostic-holdout", "evidence_grade": "Experimental",
                 "source_report_sha256": sha256_path(args.source_report), "expected_cases": expected,
                 "raw_content_included": False, "source_paths_included": False,
                 "limitations": ["Gold comes from controlled executed fault manifests, not naturally occurring incidents.",
                    "Raw view uses source-native ordinal/status codes; Panorama adds typed lifecycle semantics.",
                    "Repository and Skill identities are retained, but source content, paths, prompts, and session IDs are omitted."]},
              "cases": cases,
              "gate": {"name": "all completed executed trials converted without raw content", "passed": len(cases) == expected}}
    output = write_report(EXPERIMENT_DIR, "multirepo-diagnostic-holdout", report, args.output)
    print(json.dumps({"case_count": len(cases), "expected": expected, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
