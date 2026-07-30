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
    ("E0", "runtime_diagnostics/run_benchmark.py"),
    ("E1", "adapter_reconstruction/run_benchmark.py"),
    ("E2", "non_interference/run_benchmark.py"),
    ("E2-transport", "hook_transport/run_benchmark.py"),
    ("E3", "diagnostic_usefulness/prepare_study.py"),
    ("E4", "cross_agent/run_benchmark.py"),
    (
        "E4-source-contract",
        "cross_agent/source_instance_contract_benchmark.py",
    ),
    (
        "E4-alignment-contract",
        "cross_agent/alignment_manifest_benchmark.py",
    ),
    ("E5", "semantic_diagnosis/run_benchmark.py"),
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-live-codex", action="store_true")
    parser.add_argument("--live-trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    experiments = list(LOCAL_EXPERIMENTS)
    if arguments.include_live_codex:
        experiments.append(("E4-live-codex", "live_agent/run_codex_trials.py"))
    rows = []
    for experiment_id, relative in experiments:
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
                "exit_code": process.returncode,
                "passed": process.returncode == 0,
                "stdout_tail": process.stdout.splitlines()[-2:],
                "stderr_line_count": len(process.stderr.splitlines()),
            }
        )
    passed = all(row["passed"] for row in rows)
    report = {
        "schema_version": "sri.experiment.suite.v1",
        "experiment": {
            "name": "local-reproducibility-gates",
            "includes_live_agent_calls": arguments.include_live_codex,
        },
        "metrics": {
            "experiment_count": len(rows),
            "passed": sum(row["passed"] for row in rows),
            "failed": sum(not row["passed"] for row in rows),
        },
        "experiments": rows,
        "gate": {"name": "all selected experiment gates", "passed": passed},
    }
    output = write_report(EXPERIMENT_ROOT, "suite", report, arguments.output)
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
