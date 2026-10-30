#!/usr/bin/env python3
"""Measure the Linux/OpenBSD-netcat Unix-socket fallback independently."""

import argparse
import json
import os
import shlex
import shutil
import sys
import tempfile
import time
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.hook_transport.run_benchmark import run_paired_trials
from skill_runtime_intelligence.hook_bridge import HookBridge
from skill_runtime_intelligence.storage import Storage


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=40)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repetitions <= 0:
        parser.error("--repetitions must be positive")

    nc_path = shutil.which("nc")
    if not nc_path:
        report = {
            "schema_version": "sri.experiment.hook-nc-fallback.v1",
            "experiment": {"name": "hook-nc-fallback"},
            "metrics": {},
            "gate": {
                "name": "OpenBSD-compatible nc is available",
                "passed": False,
                "status": "not_run",
            },
        }
        output = write_report(
            EXPERIMENT_DIR, "hook-nc-fallback", report, arguments.output
        )
        print(json.dumps(report, indent=2))
        print(f"Report: {output}")
        return 2

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        database = root / "panorama.db"
        socket_path = root / "run" / "hook.sock"
        bridge = HookBridge(database, socket_path=socket_path).start()
        try:
            header = json.dumps(
                {"agent": "codex", "event": "PreToolUse"},
                separators=(",", ":"),
            )
            command = (
                f"{{ printf '%s\\n' {shlex.quote(header)}; cat; }} | "
                f"{shlex.quote(nc_path)} -N -U -w 1 "
                f"{shlex.quote(str(socket_path))}"
            )
            metrics = run_paired_trials(
                command,
                arguments.repetitions,
                "linux-nc-fallback",
                shell=True,
            )
            expected = arguments.repetitions
            deadline = time.monotonic() + 5
            counts = {}
            while time.monotonic() < deadline:
                storage = Storage(database)
                try:
                    counts = storage.counts()
                finally:
                    storage.close()
                if counts["normalized_events"] >= expected:
                    break
                time.sleep(0.02)
        finally:
            bridge.close()

    accepted = counts.get("normalized_events", 0)
    gate_passed = (
        accepted == expected
        and metrics["exit_failures"] == 0
        and metrics["non_silent_invocations"] == 0
    )
    report = {
        "schema_version": "sri.experiment.hook-nc-fallback.v1",
        "experiment": {
            "name": "hook-nc-fallback",
            "evidence_grade": "Experimental",
            "transport": "OpenBSD nc over AF_UNIX via shell",
            "container_image": os.environ.get("SRI_CONTAINER_IMAGE", ""),
            "repetitions": arguments.repetitions,
            "limitations": [
                "This measures the nc fallback, not the native sender.",
                "One local Linux container is not a cross-host estimate.",
                "Latency is descriptive and is not part of the integrity gate.",
            ],
        },
        "metrics": {
            "transport": metrics,
            "expected_events": expected,
            "accepted_events": accepted,
        },
        "gate": {
            "name": "lossless silent fallback delivery",
            "passed": gate_passed,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "hook-nc-fallback", report, arguments.output
    )
    print(
        json.dumps(
            {
                "transport": {
                    key: value
                    for key, value in metrics.items()
                    if key != "trials"
                },
                "expected_events": expected,
                "accepted_events": accepted,
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
