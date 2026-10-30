#!/usr/bin/env python3
"""Paired local microbenchmark for the fail-open Skill event collector."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import percentile, write_report
from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.hook_adapter import build_codex_hook_envelopes
from skill_runtime_intelligence.storage import Storage


def _workload(actions: int) -> Tuple[str, List[Dict[str, Any]]]:
    state = b"sri-deterministic-workload-v1"
    payloads = []
    for index in range(actions):
        action = {
            "session_id": "microbenchmark-session",
            "turn_id": "turn-1",
            "tool_name": "exec_command",
            "tool_use_id": f"call-{index}",
            "timestamp": f"2026-07-29T07:00:{index % 60:02d}Z",
            "tool_input": {"cmd": f"fixture-action-{index}"},
        }
        encoded = json.dumps(action, sort_keys=True).encode("utf-8")
        state = hashlib.sha256(state + encoded).digest()
        payloads.append(action)
    return state.hex(), payloads


def _timed_baseline(actions: int) -> Dict[str, Any]:
    cpu_start = time.process_time_ns()
    wall_start = time.perf_counter_ns()
    digest, payloads = _workload(actions)
    return {
        "digest": digest,
        "payload_digest": hashlib.sha256(
            json.dumps(payloads, sort_keys=True).encode("utf-8")
        ).hexdigest(),
        "wall_ms": (time.perf_counter_ns() - wall_start) / 1e6,
        "cpu_ms": (time.process_time_ns() - cpu_start) / 1e6,
    }


def _timed_enabled(actions: int, storage: Storage, repetition: int) -> Dict[str, Any]:
    cpu_start = time.process_time_ns()
    wall_start = time.perf_counter_ns()
    digest, payloads = _workload(actions)
    original_payload_digest = hashlib.sha256(
        json.dumps(payloads, sort_keys=True).encode("utf-8")
    ).hexdigest()
    bundles = []
    for payload in payloads:
        current = dict(payload)
        current["session_id"] = f"microbenchmark-session-{repetition}"
        current["tool_use_id"] = f"r{repetition}-{payload['tool_use_id']}"
        for hook_event in ("PreToolUse", "PostToolUse"):
            bundles.extend(
                normalize_collector_payload(
                    build_codex_hook_envelopes(hook_event, current)
                )
            )
    stored = storage.append_collector_events(bundles)
    after_payload_digest = hashlib.sha256(
        json.dumps(payloads, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return {
        "digest": digest,
        "payload_digest_before": original_payload_digest,
        "payload_digest_after": after_payload_digest,
        "wall_ms": (time.perf_counter_ns() - wall_start) / 1e6,
        "cpu_ms": (time.process_time_ns() - cpu_start) / 1e6,
        "emitted_events": len(bundles),
        **stored,
    }


def _paired_trials(actions: int, repetitions: int, database: Path) -> Dict[str, Any]:
    storage = Storage(database)
    rows = []
    try:
        for repetition in range(repetitions):
            if repetition % 2:
                enabled = _timed_enabled(actions, storage, repetition)
                baseline = _timed_baseline(actions)
            else:
                baseline = _timed_baseline(actions)
                enabled = _timed_enabled(actions, storage, repetition)
            rows.append(
                {
                    "repetition": repetition,
                    "baseline": baseline,
                    "enabled": enabled,
                    "wall_delta_ms": enabled["wall_ms"] - baseline["wall_ms"],
                    "cpu_delta_ms": enabled["cpu_ms"] - baseline["cpu_ms"],
                    "output_equal": baseline["digest"] == enabled["digest"],
                    "input_unchanged": (
                        baseline["payload_digest"]
                        == enabled["payload_digest_before"]
                        == enabled["payload_digest_after"]
                    ),
                }
            )
        counts = storage.counts()
    finally:
        storage.close()
    wall_deltas = [row["wall_delta_ms"] for row in rows]
    cpu_deltas = [row["cpu_delta_ms"] for row in rows]
    enabled_times = [row["enabled"]["wall_ms"] for row in rows]
    baseline_times = [row["baseline"]["wall_ms"] for row in rows]
    emitted = sum(row["enabled"]["emitted_events"] for row in rows)
    accepted = sum(row["enabled"]["accepted"] for row in rows)
    duplicates = sum(row["enabled"]["duplicates"] for row in rows)
    return {
        "metrics": {
            "repetitions": repetitions,
            "actions_per_repetition": actions,
            "events_per_repetition": actions * 2,
            "output_digest_mismatches": sum(not row["output_equal"] for row in rows),
            "input_mutations": sum(not row["input_unchanged"] for row in rows),
            "emitted_events": emitted,
            "accepted_events": accepted,
            "duplicate_events": duplicates,
            "missing_events": max(0, emitted - accepted - duplicates),
            "baseline_wall_p50_ms": percentile(baseline_times, 0.5),
            "baseline_wall_p95_ms": percentile(baseline_times, 0.95),
            "enabled_wall_p50_ms": percentile(enabled_times, 0.5),
            "enabled_wall_p95_ms": percentile(enabled_times, 0.95),
            "incremental_wall_p50_ms": percentile(wall_deltas, 0.5),
            "incremental_wall_p95_ms": percentile(wall_deltas, 0.95),
            "incremental_cpu_p50_ms": percentile(cpu_deltas, 0.5),
            "incremental_cpu_p95_ms": percentile(cpu_deltas, 0.95),
            "database_bytes": database.stat().st_size,
            "stored_normalized_events": counts["normalized_events"],
        },
        "trials": rows,
    }


def _subprocess_fail_open(repetitions: int, queue: Path) -> Dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
    command = [
        sys.executable,
        "-m",
        "skill_runtime_intelligence.hook_cli",
        "--agent",
        "codex",
        "--event",
        "PreToolUse",
        "--endpoint",
        "http://127.0.0.1:9/api/events",
        "--event-queue",
        str(queue),
        "--timeout-ms",
        "10",
    ]
    rows = []
    for index in range(repetitions):
        payload = {
            "session_id": f"fail-open-{index}",
            "turn_id": "turn-1",
            "tool_name": "exec_command",
            "tool_use_id": f"call-{index}",
            "timestamp": f"2026-07-29T08:00:{index % 60:02d}Z",
        }
        source = json.dumps(payload, sort_keys=True).encode("utf-8")
        start = time.perf_counter_ns()
        process = subprocess.run(
            command,
            input=source,
            capture_output=True,
            env=env,
            timeout=5,
        )
        rows.append(
            {
                "repetition": index,
                "wall_ms": (time.perf_counter_ns() - start) / 1e6,
                "exit_code": process.returncode,
                "stdout_bytes": len(process.stdout),
                "stderr_bytes": len(process.stderr),
                "input_digest": hashlib.sha256(source).hexdigest(),
            }
        )
    queued_lines = (
        sum(1 for line in queue.read_text(encoding="utf-8").splitlines() if line)
        if queue.exists()
        else 0
    )
    times = [row["wall_ms"] for row in rows]
    return {
        "metrics": {
            "repetitions": repetitions,
            "exit_failures": sum(row["exit_code"] != 0 for row in rows),
            "non_silent_invocations": sum(
                row["stdout_bytes"] or row["stderr_bytes"] for row in rows
            ),
            "queued_events": queued_lines,
            "queue_loss": max(0, repetitions - queued_lines),
            "hook_process_p50_ms": percentile(times, 0.5),
            "hook_process_p95_ms": percentile(times, 0.95),
            "queue_bytes": queue.stat().st_size if queue.exists() else 0,
        },
        "trials": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--actions", type=int, default=40)
    parser.add_argument("--repetitions", type=int, default=30)
    parser.add_argument("--hook-repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="sri-e2-") as directory:
        root = Path(directory)
        paired = _paired_trials(
            arguments.actions, arguments.repetitions, root / "events.db"
        )
        fail_open = _subprocess_fail_open(
            arguments.hook_repetitions, root / "queue" / "events.jsonl"
        )
    invariant_gate = (
        paired["metrics"]["output_digest_mismatches"] == 0
        and paired["metrics"]["input_mutations"] == 0
        and paired["metrics"]["missing_events"] == 0
        and fail_open["metrics"]["exit_failures"] == 0
        and fail_open["metrics"]["non_silent_invocations"] == 0
        and fail_open["metrics"]["queue_loss"] == 0
    )
    report = {
        "schema_version": "sri.experiment.non-interference.v1",
        "experiment": {
            "name": "local-collector-paired-microbenchmark",
            "design": "paired alternating-order deterministic workload",
            "limitations": [
                "This is an isolated local microbenchmark, not a full Agent/model trial.",
                "Latency is descriptive and does not establish negligible end-to-end overhead.",
                "Closed-port fail-open behavior is tested; process crashes and disk-full require separate fault injection.",
            ],
        },
        "paired_in_process": paired,
        "fail_open_subprocess": fail_open,
        "gate": {
            "name": "non-interference invariants",
            "passed": invariant_gate,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "non-interference", report, arguments.output
    )
    print(json.dumps(
        {
            "paired": paired["metrics"],
            "fail_open": fail_open["metrics"],
            "gate_passed": invariant_gate,
        },
        indent=2,
    ))
    print(f"Report: {output}")
    return 0 if invariant_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
