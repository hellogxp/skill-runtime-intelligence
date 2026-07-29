#!/usr/bin/env python3
"""Prepare and audit a counterbalanced diagnostic usefulness study packet."""

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.runtime_diagnostics.run_benchmark import _materialize_run
from skill_runtime_intelligence.diagnostics import (
    STAGE_INDEX,
    diagnose_skill_run,
)


def _gold_stage(case: Dict[str, Any]) -> str:
    stages = [
        finding["stage"]
        for finding in case["expected_findings"]
        if finding["stage"] in STAGE_INDEX
    ]
    return min(stages, key=STAGE_INDEX.__getitem__)


def _raw_view(run: Dict[str, Any]) -> List[str]:
    lines = [
        f"run status={run.get('status', 'unknown')}",
        f"source completeness={run.get('session_completeness', 'unknown')}",
    ]
    lines.extend(
        "event "
        + " ".join(
            (
                str(event.get("event_type", "unknown")),
                f"stage={event.get('stage', 'unknown')}",
                f"status={event.get('status', 'unknown')}",
                str(event.get("summary", "")),
            )
        )
        for event in run.get("events", [])
    )
    return lines


def _assignments(case_ids: List[str], participants: int, seed: int) -> List[dict]:
    rows = []
    for participant in range(participants):
        order = list(case_ids)
        random.Random(seed + participant).shuffle(order)
        rows.append(
            {
                "participant_slot": participant + 1,
                "case_order": [
                    {
                        "case_id": case_id,
                        "condition": (
                            "panorama"
                            if (participant + case_ids.index(case_id)) % 2
                            else "raw"
                        ),
                    }
                    for case_id in order
                ],
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=REPOSITORY_ROOT
        / "experiments"
        / "runtime_diagnostics"
        / "cases.jsonl",
    )
    parser.add_argument("--participants", type=int, default=24)
    parser.add_argument("--seed", type=int, default=20260729)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    cases = [
        case for case in load_jsonl(arguments.cases) if case["expected_findings"]
    ]
    stimuli = []
    boundary_matches = 0
    cited_findings = 0
    finding_count = 0
    for case in cases:
        run = _materialize_run(case["run"])
        findings = diagnose_skill_run(run)
        gold_stage = _gold_stage(case)
        visible_stage = findings[0]["stage"] if findings else None
        boundary_matches += visible_stage == gold_stage
        finding_count += len(findings)
        cited_findings += sum(bool(finding.get("basis")) for finding in findings)
        stimuli.append(
            {
                "case_id": case["case_id"],
                "description": case["description"],
                "raw_condition": {
                    "view": "redacted source-like event list",
                    "lines": _raw_view(run),
                },
                "panorama_condition": {
                    "view": "evidence-graded Skill Run Panorama",
                    "findings": [
                        {
                            key: finding[key]
                            for key in (
                                "title",
                                "summary",
                                "stage",
                                "severity",
                                "evidence_grade",
                                "basis",
                                "missing_signals",
                                "recommended_actions",
                            )
                        }
                        for finding in findings
                    ],
                },
            }
        )
    assignments = _assignments(
        [stimulus["case_id"] for stimulus in stimuli],
        arguments.participants,
        arguments.seed,
    )
    condition_counts = {
        case["case_id"]: {"raw": 0, "panorama": 0} for case in cases
    }
    for assignment in assignments:
        for item in assignment["case_order"]:
            condition_counts[item["case_id"]][item["condition"]] += 1
    balanced = all(
        abs(counts["raw"] - counts["panorama"]) <= 1
        for counts in condition_counts.values()
    )
    measurement_schema = [
        "participant_slot",
        "case_id",
        "condition",
        "first_boundary_answer",
        "correct",
        "elapsed_ms",
        "confidence_0_100",
        "causal_claim",
        "notes",
    ]
    metrics = {
        "case_count": len(stimuli),
        "participant_slots": arguments.participants,
        "assignment_count": len(stimuli) * arguments.participants,
        "condition_balance_passed": balanced,
        "first_visible_boundary_accuracy": boundary_matches / len(stimuli),
        "findings_with_evidence_rate": (
            cited_findings / finding_count if finding_count else 1.0
        ),
        "measurement_field_count": len(measurement_schema),
        "human_responses_collected": 0,
    }
    readiness_gate = (
        balanced
        and metrics["first_visible_boundary_accuracy"] == 1.0
        and metrics["findings_with_evidence_rate"] == 1.0
    )
    report = {
        "schema_version": "sri.experiment.diagnostic-usefulness-study.v1",
        "experiment": {
            "name": "counterbalanced-within-subject-study-readiness",
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "seed": arguments.seed,
            "status": "study-ready; no human utility claim",
            "limitations": [
                "No participant responses have been collected.",
                "The readiness audit validates stimuli, balance, evidence, and display order only.",
                "Time-to-diagnosis and correctness deltas require recruited participants.",
            ],
        },
        "metrics": metrics,
        "measurement_schema": measurement_schema,
        "condition_counts": condition_counts,
        "assignments": assignments,
        "stimuli": stimuli,
        "gold_labels": [
            {"case_id": case["case_id"], "first_boundary": _gold_stage(case)}
            for case in cases
        ],
        "gate": {"name": "study readiness", "passed": readiness_gate},
    }
    output = write_report(
        EXPERIMENT_DIR, "diagnostic-usefulness-study", report, arguments.output
    )
    print(json.dumps({"metrics": metrics, "gate_passed": readiness_gate}, indent=2))
    print(f"Report: {output}")
    return 0 if readiness_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())

