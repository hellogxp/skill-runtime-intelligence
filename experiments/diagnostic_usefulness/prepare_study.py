#!/usr/bin/env python3
"""Prepare and audit a counterbalanced model-agent usefulness study packet."""

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


def _assignments(case_ids: List[str], model_samples: int, seed: int) -> List[dict]:
    rows = []
    for sample in range(model_samples):
        order = list(case_ids)
        random.Random(seed + sample).shuffle(order)
        rows.append(
            {
                "model_sample_slot": sample + 1,
                "case_order": [
                    {
                        "case_id": case_id,
                        "condition": (
                            "panorama"
                            if (sample + case_ids.index(case_id)) % 2
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
    parser.add_argument(
        "--model-samples",
        "--participants",
        dest="model_samples",
        type=int,
        default=24,
        help=(
            "Independent model-session sample slots. --participants is kept "
            "only as a compatibility alias."
        ),
    )
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
                                "causal_scope",
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
        arguments.model_samples,
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
        "model_sample_slot",
        "model_provider",
        "model_id",
        "model_cli_version",
        "prompt_sha256",
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
        "model_sample_slots": arguments.model_samples,
        "planned_model_trials": len(stimuli) * arguments.model_samples,
        "condition_balance_passed": balanced,
        "first_visible_boundary_accuracy": boundary_matches / len(stimuli),
        "findings_with_evidence_rate": (
            cited_findings / finding_count if finding_count else 1.0
        ),
        "measurement_field_count": len(measurement_schema),
        "model_responses_collected": 0,
    }
    readiness_gate = (
        balanced
        and metrics["first_visible_boundary_accuracy"] == 1.0
        and metrics["findings_with_evidence_rate"] == 1.0
    )
    report = {
        "schema_version": "sri.experiment.model-agent-usefulness-study.v1",
        "experiment": {
            "name": "counterbalanced-model-agent-study-readiness",
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "seed": arguments.seed,
            "status": "model-agent study ready; no response or human utility claim",
            "limitations": [
                "No model responses are collected by this preparation step.",
                "The readiness audit validates stimuli, balance, evidence, and display order only.",
                "Repeated sessions from one model are stochastic samples, not independent people or independent model families.",
                "Any completed result applies to the recorded model and prompt protocol, not to human usability.",
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
