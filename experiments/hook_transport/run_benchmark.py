#!/usr/bin/env python3
"""Measure native Unix-socket hook transport overhead against process startup."""

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import tempfile
import time
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import percentile, write_report
from skill_runtime_intelligence.hook_bridge import HookBridge
from skill_runtime_intelligence.native_sender import build_native_hook_sender
from skill_runtime_intelligence.storage import Storage


def load_average():
    try:
        one, five, fifteen = os.getloadavg()
    except (AttributeError, OSError):
        return None
    return {"one_minute": one, "five_minutes": five, "fifteen_minutes": fifteen}


def run_process(command, payload, shell=False):
    started = time.perf_counter_ns()
    process = subprocess.run(
        command,
        shell=shell,
        input=payload,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=3,
    )
    return {
        "wall_ms": (time.perf_counter_ns() - started) / 1e6,
        "exit_code": process.returncode,
        "stdout_bytes": len(process.stdout),
        "stderr_bytes": len(process.stderr),
    }


def run_paired_trials(command, repetitions, prefix, shell=False):
    rows = []
    for index in range(repetitions):
        payload = json.dumps(
            {
                "session_id": f"{prefix}-{index}",
                "turn_id": "turn-1",
                "tool_name": "Skill",
                "tool_use_id": f"call-{index}",
                "tool_input": {"skill": "transport-fixture"},
            },
            separators=(",", ":"),
        ).encode("utf-8")
        if index % 2:
            actual = run_process(command, payload, shell=shell)
            baseline = run_process(["/usr/bin/true"], payload)
            order = "actual_first"
        else:
            baseline = run_process(["/usr/bin/true"], payload)
            actual = run_process(command, payload, shell=shell)
            order = "baseline_first"
        rows.append(
            {
                "repetition": index,
                "order": order,
                "baseline_wall_ms": baseline["wall_ms"],
                "actual_wall_ms": actual["wall_ms"],
                "incremental_wall_ms": actual["wall_ms"] - baseline["wall_ms"],
                "exit_code": actual["exit_code"],
                "stdout_bytes": actual["stdout_bytes"],
                "stderr_bytes": actual["stderr_bytes"],
            }
        )
    actual_times = [row["actual_wall_ms"] for row in rows]
    baseline_times = [row["baseline_wall_ms"] for row in rows]
    deltas = [row["incremental_wall_ms"] for row in rows]
    return {
        "repetitions": repetitions,
        "baseline_p50_ms": percentile(baseline_times, 0.5),
        "baseline_p95_ms": percentile(baseline_times, 0.95),
        "actual_p50_ms": percentile(actual_times, 0.5),
        "actual_p95_ms": percentile(actual_times, 0.95),
        "actual_p99_ms": percentile(actual_times, 0.99),
        "actual_max_ms": max(actual_times),
        "incremental_p50_ms": percentile(deltas, 0.5),
        "incremental_p95_ms": percentile(deltas, 0.95),
        "incremental_p99_ms": percentile(deltas, 0.99),
        "exit_failures": sum(row["exit_code"] != 0 for row in rows),
        "non_silent_invocations": sum(
            bool(row["stdout_bytes"] or row["stderr_bytes"]) for row in rows
        ),
        "trials": rows,
    }


def run_interleaved_conditions(
    direct_command,
    shell_command,
    repetitions,
    prefix="interleaved",
):
    rows = {"direct": [], "shell": []}
    conditions = {
        "direct": (direct_command, False),
        "shell": (shell_command, True),
    }
    for index in range(repetitions):
        condition_order = (
            ("direct", "shell") if index % 2 == 0 else ("shell", "direct")
        )
        for position, label in enumerate(condition_order):
            command, use_shell = conditions[label]
            payload = json.dumps(
                {
                    "session_id": f"{prefix}-{label}-{index}",
                    "turn_id": "turn-1",
                    "tool_name": "Skill",
                    "tool_use_id": f"call-{index}",
                    "tool_input": {"skill": "transport-fixture"},
                },
                separators=(",", ":"),
            ).encode("utf-8")
            # Four-run Williams-style balance.  For each transport, every
            # (condition position, measurement order) combination occurs once
            # per block instead of letting position determine order.
            actual_first = index % 4 in (1, 2)
            if actual_first:
                actual = run_process(command, payload, shell=use_shell)
                baseline = run_process(["/usr/bin/true"], payload)
                order = "actual_first"
            else:
                baseline = run_process(["/usr/bin/true"], payload)
                actual = run_process(command, payload, shell=use_shell)
                order = "baseline_first"
            rows[label].append(
                {
                    "repetition": index,
                    "condition_position": position,
                    "order": order,
                    "baseline_wall_ms": baseline["wall_ms"],
                    "actual_wall_ms": actual["wall_ms"],
                    "incremental_wall_ms": (
                        actual["wall_ms"] - baseline["wall_ms"]
                    ),
                    "exit_code": actual["exit_code"],
                    "stdout_bytes": actual["stdout_bytes"],
                    "stderr_bytes": actual["stderr_bytes"],
                }
            )

    def summarize(condition_rows):
        actual_times = [row["actual_wall_ms"] for row in condition_rows]
        baseline_times = [row["baseline_wall_ms"] for row in condition_rows]
        deltas = [row["incremental_wall_ms"] for row in condition_rows]
        steady_rows = condition_rows[min(5, len(condition_rows)) :]
        steady_actual = [row["actual_wall_ms"] for row in steady_rows]
        steady_deltas = [row["incremental_wall_ms"] for row in steady_rows]
        design_balance = {
            f"position_{position}_{order}": sum(
                row["condition_position"] == position and row["order"] == order
                for row in condition_rows
            )
            for position in (0, 1)
            for order in ("baseline_first", "actual_first")
        }
        return {
            "repetitions": len(condition_rows),
            "baseline_p50_ms": percentile(baseline_times, 0.5),
            "baseline_p95_ms": percentile(baseline_times, 0.95),
            "actual_p50_ms": percentile(actual_times, 0.5),
            "actual_p95_ms": percentile(actual_times, 0.95),
            "actual_p99_ms": percentile(actual_times, 0.99),
            "actual_max_ms": max(actual_times),
            "incremental_p50_ms": percentile(deltas, 0.5),
            "incremental_p95_ms": percentile(deltas, 0.95),
            "incremental_p99_ms": percentile(deltas, 0.99),
            "first_five_actual_max_ms": max(actual_times[:5]),
            "post_five_actual_p95_ms": percentile(steady_actual, 0.95),
            "post_five_incremental_p95_ms": percentile(steady_deltas, 0.95),
            "design_balance": design_balance,
            "exit_failures": sum(
                row["exit_code"] != 0 for row in condition_rows
            ),
            "non_silent_invocations": sum(
                bool(row["stdout_bytes"] or row["stderr_bytes"])
                for row in condition_rows
            ),
            "trials": condition_rows,
        }

    return {label: summarize(condition_rows) for label, condition_rows in rows.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=40)
    parser.add_argument(
        "--prewarm-native",
        action="store_true",
        help="Execute the fresh binary once against a missing socket before trials",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repetitions <= 0 or arguments.repetitions % 4:
        parser.error("--repetitions must be a positive multiple of 4")
    ambient_at_start = load_average()
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        build = build_native_hook_sender(root)
        if not build["available"]:
            report = {
                "schema_version": "sri.experiment.hook-transport.v1",
                "experiment": {"name": "hook-transport", "build": build},
                "metrics": {},
                "gate": {"name": "native sender available", "passed": False},
            }
            output = write_report(
                EXPERIMENT_DIR, "hook-transport", report, arguments.output
            )
            print(json.dumps(report["gate"], indent=2))
            print(f"Report: {output}")
            return 1

        database = root / "panorama.db"
        socket_path = root / "run" / "hook.sock"
        bridge = HookBridge(database, socket_path=socket_path).start()
        try:
            native_command = [
                build["path"],
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
                "--socket",
                str(socket_path),
            ]
            prewarm = None
            if arguments.prewarm_native:
                prewarm_command = list(native_command)
                prewarm_command[-1] = str(root / "run" / "prewarm-missing.sock")
                prewarm = run_process(prewarm_command, b"{}")
            shell_command = " ".join(shlex.quote(part) for part in native_command)
            interleaved = run_interleaved_conditions(
                native_command,
                shell_command,
                arguments.repetitions,
            )
            direct = interleaved["direct"]
            shell_native = interleaved["shell"]
            nc = None
            nc_path = Path("/usr/bin/nc")
            if nc_path.is_file() and sys.platform != "darwin":
                header = json.dumps(
                    {"agent": "codex", "event": "PreToolUse"},
                    separators=(",", ":"),
                )
                nc_command = (
                    f"{{ printf '%s\\n' {shlex.quote(header)}; cat; }} | "
                    f"{shlex.quote(str(nc_path))} -N -U -w 1 "
                    f"{shlex.quote(str(socket_path))}"
                )
                nc = run_paired_trials(
                    nc_command,
                    arguments.repetitions,
                    "nc-shell",
                    shell=True,
                )
            deadline = time.monotonic() + 5
            expected = arguments.repetitions * (2 + (1 if nc else 0))
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

    gate_passed = (
        direct["exit_failures"] == 0
        and shell_native["exit_failures"] == 0
        and direct["non_silent_invocations"] == 0
        and shell_native["non_silent_invocations"] == 0
        and counts.get("normalized_events", 0) == expected
        and direct["actual_p95_ms"] < 100
        and shell_native["actual_p95_ms"] < 100
        and shell_native["incremental_p95_ms"] < 75
        and set(direct["design_balance"].values())
        == {arguments.repetitions // 4}
        and set(shell_native["design_balance"].values())
        == {arguments.repetitions // 4}
        and (
            prewarm is None
            or (
                prewarm["exit_code"] == 1
                and prewarm["stdout_bytes"] == 0
                and prewarm["stderr_bytes"] == 0
            )
        )
    )
    schema_version = (
        "sri.experiment.hook-transport-prewarmed.v1"
        if arguments.prewarm_native
        else "sri.experiment.hook-transport.v6"
    )
    report = {
        "schema_version": schema_version,
        "experiment": {
            "name": "hook-transport",
            "repetitions": arguments.repetitions,
            "payloads_contain_secrets": False,
            "native_prewarmed": arguments.prewarm_native,
            "design": (
                "interleaved direct/shell conditions with four-run balance over "
                "condition position and baseline/actual order"
            ),
            "engineering_slo": {
                "direct_actual_p95_ms": 100,
                "shell_actual_p95_ms": 100,
                "shell_incremental_p95_ms": 75,
            },
            "host_load": {
                "logical_cpu_count": os.cpu_count(),
                "ambient_at_start": ambient_at_start,
                "ambient_at_end": load_average(),
            },
            "runtime_environment": {
                "system": platform.system().lower(),
                "machine": platform.machine().lower(),
                "python": platform.python_version(),
                "container_marker_present": Path("/.dockerenv").exists(),
            },
            "limitations": [
                "The SLO is a local engineering gate, not a cross-platform claim.",
                "Agent scheduling and model latency are outside this transport benchmark.",
                "Post-first-five metrics diagnose warmup but do not replace the full-run gate.",
                "Earlier v1/v2/v3 runs are not pooled; v4/v5/v6 share the same design and gate.",
                "Load averages are descriptive covariates, not utilization measurements.",
            ],
        },
        "metrics": {
            "prewarm": prewarm,
            "native_direct": direct,
            "native_via_shell": shell_native,
            "nc_via_shell": nc,
            "expected_events": expected,
            "accepted_events": counts.get("normalized_events", 0),
        },
        "gate": {
            "name": (
                "lossless silent delivery; direct/shell p95 below 100 ms; "
                "shell incremental p95 below 75 ms"
            ),
            "passed": gate_passed,
        },
    }
    report_name = (
        "hook-transport-prewarmed"
        if arguments.prewarm_native
        else "hook-transport"
    )
    output = write_report(EXPERIMENT_DIR, report_name, report, arguments.output)
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
