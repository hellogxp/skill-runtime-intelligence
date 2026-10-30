#!/usr/bin/env python3
"""Explore native hook transport under bounded local CPU and I/O contention."""

import argparse
import json
import os
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
from experiments.hook_transport.run_benchmark import run_interleaved_conditions
from skill_runtime_intelligence.hook_bridge import HookBridge
from skill_runtime_intelligence.native_sender import build_native_hook_sender
from skill_runtime_intelligence.storage import Storage


CPU_WORKER = """
x = 1
while True:
    x = (x * 1664525 + 1013904223) & 0xffffffff
"""

IO_WORKER = """
import os
import sys
path = sys.argv[1]
block = b"x" * (1024 * 1024)
with open(path, "w+b", buffering=0) as stream:
    while True:
        stream.seek(0)
        stream.write(block)
        os.fsync(stream.fileno())
"""


def start_load(kind, root):
    workers = []
    cpu_workers = min(4, max(1, (os.cpu_count() or 2) // 2))
    if kind in {"cpu", "mixed"}:
        count = cpu_workers if kind == "cpu" else max(1, cpu_workers // 2)
        for _ in range(count):
            workers.append(
                subprocess.Popen(
                    [sys.executable, "-c", CPU_WORKER],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            )
    if kind in {"io", "mixed"}:
        workers.append(
            subprocess.Popen(
                [sys.executable, "-c", IO_WORKER, str(root / f"{kind}.bin")],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        )
    if workers:
        time.sleep(0.25)
    return workers


def stop_load(workers):
    premature_exit_codes = [
        worker.returncode for worker in workers if worker.poll() is not None
    ]
    for worker in workers:
        if worker.poll() is None:
            worker.terminate()
    for worker in workers:
        try:
            worker.wait(timeout=2)
        except subprocess.TimeoutExpired:
            worker.kill()
            worker.wait(timeout=2)
    return premature_exit_codes


def summarize_rows(rows):
    actual = [row["actual_wall_ms"] for row in rows]
    incremental = [row["incremental_wall_ms"] for row in rows]
    return {
        "trials": len(rows),
        "actual_p50_ms": percentile(actual, 0.5),
        "actual_p95_ms": percentile(actual, 0.95),
        "actual_max_ms": max(actual),
        "incremental_p50_ms": percentile(incremental, 0.5),
        "incremental_p95_ms": percentile(incremental, 0.95),
    }


def ratio(value, baseline):
    return value / baseline if baseline else None


def load_average():
    try:
        one, five, fifteen = os.getloadavg()
    except (AttributeError, OSError):
        return None
    return {"one_minute": one, "five_minutes": five, "fifteen_minutes": fifteen}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=16)
    parser.add_argument(
        "--schedule-order",
        choices=("forward", "reverse"),
        default="forward",
    )
    parser.add_argument(
        "--max-ambient-load-per-cpu",
        type=float,
        default=0.75,
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repetitions <= 0 or arguments.repetitions % 4:
        parser.error("--repetitions must be a positive multiple of 4")
    logical_cpu_count = os.cpu_count() or 1
    ambient_at_start = load_average()
    if (
        ambient_at_start
        and ambient_at_start["one_minute"] / logical_cpu_count
        > arguments.max_ambient_load_per_cpu
    ):
        report = {
            "schema_version": "sri.experiment.hook-contention.v2",
            "experiment": {
                "name": "hook-contention",
                "evidence_grade": "Observed",
                "status": "not_run",
                "reason": "ambient load exceeded the predeclared safety limit",
                "max_ambient_load_per_cpu": (
                    arguments.max_ambient_load_per_cpu
                ),
            },
            "metrics": {
                "logical_cpu_count": logical_cpu_count,
                "ambient_load_average": ambient_at_start,
                "ambient_one_minute_load_per_cpu": (
                    ambient_at_start["one_minute"] / logical_cpu_count
                ),
            },
            "gate": {
                "name": "ambient load safety precondition",
                "passed": False,
                "status": "not_run",
            },
        }
        output = write_report(
            EXPERIMENT_DIR, "hook-contention", report, arguments.output
        )
        print(json.dumps(report, indent=2))
        print(f"Report: {output}")
        return 2

    middle = (
        ("cpu", "io", "mixed")
        if arguments.schedule_order == "forward"
        else ("mixed", "io", "cpu")
    )
    schedule = ("idle_pre", *middle, "idle_post")
    segments = {}
    premature_exits = {}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        build = build_native_hook_sender(root)
        if not build["available"]:
            report = {
                "schema_version": "sri.experiment.hook-contention.v1",
                "experiment": {"name": "hook-contention", "build": build},
                "metrics": {},
                "gate": {"name": "native sender available", "passed": False},
            }
            output = write_report(
                EXPERIMENT_DIR, "hook-contention", report, arguments.output
            )
            print(json.dumps(report["gate"], indent=2))
            print(f"Report: {output}")
            return 1

        database = root / "panorama.db"
        socket_path = root / "run" / "hook.sock"
        bridge = HookBridge(database, socket_path=socket_path).start()
        try:
            direct_command = [
                build["path"],
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
                "--socket",
                str(socket_path),
            ]
            shell_command = " ".join(
                shlex.quote(part) for part in direct_command
            )
            for segment in schedule:
                ambient_before = load_average()
                load_kind = segment.removeprefix("idle_")
                if segment.startswith("idle_"):
                    load_kind = "idle"
                workers = start_load(load_kind, root)
                ambient_after_load_start = load_average()
                started = time.monotonic()
                try:
                    result = run_interleaved_conditions(
                        direct_command,
                        shell_command,
                        arguments.repetitions,
                        prefix=f"contention-{segment}",
                    )
                    workers_alive = all(
                        worker.poll() is None for worker in workers
                    )
                    ambient_before_load_stop = load_average()
                finally:
                    premature_exits[segment] = stop_load(workers)
                segments[segment] = {
                    "load_kind": load_kind,
                    "load_worker_count": len(workers),
                    "load_workers_alive_during_measurement": workers_alive,
                    "ambient_load_before": ambient_before,
                    "ambient_load_after_load_start": ambient_after_load_start,
                    "ambient_load_before_load_stop": ambient_before_load_stop,
                    "duration_seconds": time.monotonic() - started,
                    "native_direct": result["direct"],
                    "native_via_shell": result["shell"],
                }

            expected = len(schedule) * arguments.repetitions * 2
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

    idle_rows = {
        transport: (
            segments["idle_pre"][transport]["trials"]
            + segments["idle_post"][transport]["trials"]
        )
        for transport in ("native_direct", "native_via_shell")
    }
    idle = {
        transport: summarize_rows(rows) for transport, rows in idle_rows.items()
    }
    comparisons = {}
    for segment in ("cpu", "io", "mixed"):
        comparisons[segment] = {}
        for transport in ("native_direct", "native_via_shell"):
            summary = summarize_rows(segments[segment][transport]["trials"])
            baseline = idle[transport]
            comparisons[segment][transport] = {
                **summary,
                "actual_p50_ratio_to_pooled_idle": ratio(
                    summary["actual_p50_ms"], baseline["actual_p50_ms"]
                ),
                "actual_p95_ratio_to_pooled_idle": ratio(
                    summary["actual_p95_ms"], baseline["actual_p95_ms"]
                ),
                "incremental_p95_ratio_to_pooled_idle": ratio(
                    summary["incremental_p95_ms"],
                    baseline["incremental_p95_ms"],
                ),
            }

    all_transport_results = [
        segments[segment][transport]
        for segment in schedule
        for transport in ("native_direct", "native_via_shell")
    ]
    worker_health = all(
        not premature_exits[segment]
        and segments[segment]["load_workers_alive_during_measurement"]
        for segment in ("cpu", "io", "mixed")
    )
    expected = len(schedule) * arguments.repetitions * 2
    accepted = counts.get("normalized_events", 0)
    gate_passed = (
        worker_health
        and accepted == expected
        and all(result["exit_failures"] == 0 for result in all_transport_results)
        and all(
            result["non_silent_invocations"] == 0
            for result in all_transport_results
        )
    )
    report = {
        "schema_version": "sri.experiment.hook-contention.v2",
        "experiment": {
            "name": "hook-contention",
            "evidence_grade": "Experimental",
            "schedule": schedule,
            "schedule_order": arguments.schedule_order,
            "logical_cpu_count": logical_cpu_count,
            "ambient_load_at_start": ambient_at_start,
            "max_ambient_load_per_cpu": arguments.max_ambient_load_per_cpu,
            "repetitions_per_segment": arguments.repetitions,
            "hypothesis": (
                "bounded CPU/I/O contention is associated with a larger "
                "upper-tail change than median change"
            ),
            "design": (
                "idle bookends with balanced direct/shell and measurement "
                "order inside each segment"
            ),
            "limitations": [
                "Single-host exploratory run; ratios are not causal estimates.",
                "Load segments are sequential and may retain temporal bias.",
                "Synthetic load does not represent every Agent workload.",
                "Load averages are descriptive and respond slowly to segment changes.",
            ],
        },
        "metrics": {
            "expected_events": expected,
            "accepted_events": accepted,
            "pooled_idle": idle,
            "contention_comparisons": comparisons,
            "segments": segments,
            "premature_worker_exit_codes": premature_exits,
        },
        "gate": {
            "name": "healthy bounded load with lossless silent delivery",
            "passed": gate_passed,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "hook-contention", report, arguments.output
    )
    print(
        json.dumps(
            {
                "pooled_idle": idle,
                "contention_comparisons": comparisons,
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
