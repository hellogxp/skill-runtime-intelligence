#!/usr/bin/env python3
"""Run the reproducible local SRI experiment gates as one suite."""

import argparse
import json
import subprocess
import sys
from pathlib import Path


EXPERIMENT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_ROOT.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


LOCAL_EXPERIMENTS = (
    ("E0", "runtime_diagnostics/run_benchmark.py", "correctness"),
    ("E1", "adapter_reconstruction/run_benchmark.py", "correctness"),
    ("E2", "non_interference/run_benchmark.py", "correctness"),
    (
        "E2-transport",
        "hook_transport/run_benchmark.py",
        "environment_sensitive",
    ),
    ("E3", "diagnostic_usefulness/prepare_study.py", "correctness"),
    ("E4", "cross_agent/run_benchmark.py", "correctness"),
    (
        "E4-source-contract",
        "cross_agent/source_instance_contract_benchmark.py",
        "correctness",
    ),
    (
        "E4-alignment-contract",
        "cross_agent/alignment_manifest_benchmark.py",
        "correctness",
    ),
    (
        "E4-clock-sensitivity",
        "cross_agent/alignment_clock_sensitivity.py",
        "correctness",
    ),
    (
        "E4-timestamp-capability",
        "cross_agent/timestamp_provenance_audit.py",
        "correctness",
    ),
    (
        "E4-timestamp-partial-migration",
        "product_lifecycle/migration_partial_state_benchmark.py",
        "correctness",
    ),
    (
        "E4-timestamp-kill-recovery",
        "product_lifecycle/migration_kill_recovery_benchmark.py",
        "correctness",
    ),
    ("E5", "semantic_diagnosis/run_benchmark.py", "correctness"),
)


def _summarize(rows):
    classes = {}
    for row in rows:
        gate_class = row["gate_class"]
        aggregate = classes.setdefault(
            gate_class,
            {"experiment_count": 0, "passed": 0, "failed": 0},
        )
        aggregate["experiment_count"] += 1
        aggregate["passed"] += int(row["passed"])
        aggregate["failed"] += int(not row["passed"])
    correctness_rows = [
        row for row in rows if row["gate_class"] == "correctness"
    ]
    return {
        "experiment_count": len(rows),
        "passed": sum(row["passed"] for row in rows),
        "failed": sum(not row["passed"] for row in rows),
        "by_gate_class": classes,
        "correctness_core_passed": all(
            row["passed"] for row in correctness_rows
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-live-codex", action="store_true")
    parser.add_argument("--live-trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    experiments = list(LOCAL_EXPERIMENTS)
    if arguments.include_live_codex:
        experiments.append(
            (
                "E4-live-codex",
                "live_agent/run_codex_trials.py",
                "live_external",
            )
        )
    rows = []
    for experiment_id, relative, gate_class in experiments:
        command = [
            sys.executable,
            str(EXPERIMENT_ROOT / relative),
        ]
        if experiment_id == "E4-live-codex":
            command.extend(["--trials", str(arguments.live_trials)])
        process = subprocess.run(
            command,
            cwd=REPOSITORY_ROOT,
            capture_output=True,
            text=True,
            timeout=600,
        )
        rows.append(
            {
                "experiment_id": experiment_id,
                "runner": relative,
                "gate_class": gate_class,
                "exit_code": process.returncode,
                "passed": process.returncode == 0,
                "stdout_tail": process.stdout.splitlines()[-2:],
                "stderr_line_count": len(process.stderr.splitlines()),
            }
        )
    passed = all(row["passed"] for row in rows)
    metrics = _summarize(rows)
    report = {
        "schema_version": "sri.experiment.suite.v2",
        "experiment": {
            "name": "local-reproducibility-gates",
            "includes_live_agent_calls": arguments.include_live_codex,
        },
        "metrics": metrics,
        "experiments": rows,
        "gate": {"name": "all selected experiment gates", "passed": passed},
        "correctness_core_gate": {
            "name": "all deterministic correctness gates",
            "passed": metrics["correctness_core_passed"],
        },
    }
    output = write_report(EXPERIMENT_ROOT, "suite", report, arguments.output)
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
