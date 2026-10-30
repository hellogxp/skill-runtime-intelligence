#!/usr/bin/env python3
"""Freeze paired controlled cases for rule-external anomaly discovery."""

import argparse
import json
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


def _case(identifier, family, anomaly, evidence, support):
    return {"case_id": identifier, "family": family, "anomaly_present": anomaly,
            "evidence": evidence, "expected_support": support,
            "label_origin": "preregistered_controlled_graph_invariant"}


def build_cases():
    definitions = [
        ("temporal_order", [{"evidence_id": "E1", "kind": "event", "stage": "activation", "sequence": 2},
                            {"evidence_id": "E2", "kind": "event", "stage": "execution", "sequence": 1}],
                           [{"evidence_id": "E1", "kind": "event", "stage": "activation", "sequence": 1},
                            {"evidence_id": "E2", "kind": "event", "stage": "execution", "sequence": 2}]),
        ("parent_cycle", [{"evidence_id": "E1", "kind": "event", "parent": "E2"}, {"evidence_id": "E2", "kind": "event", "parent": "E1"}],
                         [{"evidence_id": "E1", "kind": "event", "parent": None}, {"evidence_id": "E2", "kind": "event", "parent": "E1"}]),
        ("evidence_grade_escalation", [{"evidence_id": "E1", "kind": "source", "grade": "derived"}, {"evidence_id": "E2", "kind": "claim", "grade": "observed", "depends_on": ["E1"]}],
                                      [{"evidence_id": "E1", "kind": "source", "grade": "derived"}, {"evidence_id": "E2", "kind": "claim", "grade": "derived", "depends_on": ["E1"]}]),
        ("verifier_conflict", [{"evidence_id": "E1", "kind": "reported_outcome", "status": "success"}, {"evidence_id": "E2", "kind": "independent_verifier", "status": "failed"}],
                              [{"evidence_id": "E1", "kind": "reported_outcome", "status": "success"}, {"evidence_id": "E2", "kind": "independent_verifier", "status": "passed"}]),
        ("capability_drift", [{"evidence_id": "E1", "kind": "adapter_contract", "outcome_events": "unsupported"}, {"evidence_id": "E2", "kind": "normalized_event", "event_type": "outcome.verified", "adapter": "same"}],
                             [{"evidence_id": "E1", "kind": "adapter_contract", "outcome_events": "supported"}, {"evidence_id": "E2", "kind": "normalized_event", "event_type": "outcome.verified", "adapter": "same"}]),
        ("orphan_reference", [{"evidence_id": "E1", "kind": "session", "session_key": "S1"}, {"evidence_id": "E2", "kind": "attempt", "session_key": "S2"}],
                             [{"evidence_id": "E1", "kind": "session", "session_key": "S1"}, {"evidence_id": "E2", "kind": "attempt", "session_key": "S1"}]),
    ]
    cases = []
    for index, (family, anomaly, clean) in enumerate(definitions, 1):
        cases.append(_case(f"novel-{index:02d}-anomaly", family, True, anomaly, ["E1", "E2"]))
        cases.append(_case(f"novel-{index:02d}-clean", family, False, clean, []))
    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = {"schema_version": "sri.experiment.novel-pattern-holdout.v1",
              "experiment": {"name": "paired-rule-external-graph-anomaly-holdout", "evidence_grade": "Experimental",
                 "preregistered_families": [case["family"] for case in build_cases() if case["anomaly_present"]],
                 "limitations": ["Cases are controlled synthetic graph invariants, not production incidents.",
                    "The holdout tests hypothesis generation and false positives, not prevalence."]},
              "cases": build_cases(),
              "gate": {"name": "six balanced anomaly/clean families", "passed": len(build_cases()) == 12}}
    output = write_report(EXPERIMENT_DIR, "novel-pattern-holdout", report, args.output)
    print(json.dumps({"cases": len(report["cases"]), "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
