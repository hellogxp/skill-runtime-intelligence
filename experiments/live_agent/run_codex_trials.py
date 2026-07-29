#!/usr/bin/env python3
"""Run repeated read-only Codex trials on the deterministic Skill fixture."""

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
FIXTURE = EXPERIMENT_DIR / "fixture"
SKILL_FILE = FIXTURE / ".agents" / "skills" / "checksum-skill" / "SKILL.md"
TASK_FILE = FIXTURE / "task.txt"
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import percentile, sha256_path, write_report
from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.discovery import parse_skill


def _fixture_digest() -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in FIXTURE.rglob("*") if path.is_file()):
        relative = path.relative_to(FIXTURE)
        digest.update(str(relative).encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _expected() -> str:
    script = SKILL_FILE.parent / "scripts" / "verify.py"
    return subprocess.run(
        [sys.executable, str(script)],
        cwd=FIXTURE,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _session_file(thread_id: str) -> Optional[Path]:
    root = Path.home() / ".codex" / "sessions"
    matches = list(root.rglob(f"*{thread_id}*.jsonl")) if root.is_dir() else []
    return max(matches, key=lambda path: path.stat().st_mtime_ns) if matches else None


def _run_trial(index: int, model: str, ignore_user_config: bool) -> Dict[str, Any]:
    before = _fixture_digest()
    command = [
        "codex",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--model",
        model,
    ]
    if ignore_user_config:
        command.append("--ignore-user-config")
    command.append("-")
    started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=FIXTURE,
        input=TASK_FILE.read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=180,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000
    records = []
    for line in process.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    thread_id = next(
        (
            record.get("thread_id")
            for record in records
            if record.get("type") == "thread.started"
        ),
        None,
    )
    completed = next(
        (
            record
            for record in reversed(records)
            if record.get("type") == "turn.completed"
        ),
        {},
    )
    final = next(
        (
            record.get("item", {}).get("text")
            for record in reversed(records)
            if record.get("type") == "item.completed"
            and record.get("item", {}).get("type") == "agent_message"
        ),
        "",
    )
    session_path = _session_file(str(thread_id or ""))
    for _ in range(10):
        if session_path:
            break
        time.sleep(0.1)
        session_path = _session_file(str(thread_id or ""))
    reconstructed: Dict[str, Any] = {
        "session_found": bool(session_path),
        "skill_run_count": 0,
        "skill_event_types": [],
    }
    if session_path:
        skill = parse_skill(SKILL_FILE)
        session, raw, events, runs = CodexAdapter(session_path.parent).parse(
            session_path, [skill]
        )
        reconstructed = {
            "session_found": True,
            "session_status": session["status"],
            "session_completeness": session["completeness"],
            "session_duration_ms": session["duration_ms"],
            "raw_record_count": len(raw),
            "normalized_event_count": len(events),
            "skill_run_count": len(runs),
            "skill_event_types": [
                event["event_type"] for event in events if event.get("skill_id")
            ],
            "skill_run_evidence_grades": sorted(
                {run["evidence_grade"] for run in runs}
            ),
        }
    expected = _expected()
    after = _fixture_digest()
    usage = completed.get("usage", {})
    return {
        "trial": index,
        "thread_id": thread_id,
        "exit_code": process.returncode,
        "wall_ms": elapsed_ms,
        "usage": {
            key: usage.get(key)
            for key in (
                "input_tokens",
                "cached_input_tokens",
                "output_tokens",
                "reasoning_output_tokens",
            )
        },
        "final_response_sha256": hashlib.sha256(
            str(final).encode("utf-8")
        ).hexdigest(),
        "expected_response_sha256": hashlib.sha256(
            expected.encode("utf-8")
        ).hexdigest(),
        "outcome_verified": final == expected,
        "workspace_unchanged": before == after,
        "stderr_line_count": len(process.stderr.splitlines()),
        "reconstruction": reconstructed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument(
        "--load-user-config",
        action="store_true",
        help="Load user config; ignored by default to reduce unrelated variability.",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    rows = [
        _run_trial(
            index + 1,
            arguments.model,
            ignore_user_config=not arguments.load_user_config,
        )
        for index in range(arguments.trials)
    ]
    inputs = [
        row["usage"]["input_tokens"]
        for row in rows
        if isinstance(row["usage"]["input_tokens"], (int, float))
    ]
    walls = [row["wall_ms"] for row in rows]
    metrics = {
        "trial_count": len(rows),
        "verified_outcomes": sum(row["outcome_verified"] for row in rows),
        "workspace_mutations": sum(not row["workspace_unchanged"] for row in rows),
        "process_failures": sum(row["exit_code"] != 0 for row in rows),
        "sessions_reconstructed": sum(
            row["reconstruction"]["session_found"] for row in rows
        ),
        "skill_runs_reconstructed": sum(
            row["reconstruction"]["skill_run_count"] == 1 for row in rows
        ),
        "instruction_events_reconstructed": sum(
            "instruction.loaded" in row["reconstruction"]["skill_event_types"]
            for row in rows
        ),
        "resource_events_reconstructed": sum(
            "resource.executed" in row["reconstruction"]["skill_event_types"]
            for row in rows
        ),
        "wall_p50_ms": percentile(walls, 0.5),
        "wall_p95_ms": percentile(walls, 0.95),
        "input_tokens_p50": percentile(inputs, 0.5),
        "input_tokens_p95": percentile(inputs, 0.95),
    }
    passed = (
        metrics["verified_outcomes"] == len(rows)
        and metrics["workspace_mutations"] == 0
        and metrics["process_failures"] == 0
        and metrics["sessions_reconstructed"] == len(rows)
        and metrics["skill_runs_reconstructed"] == len(rows)
        and metrics["instruction_events_reconstructed"] == len(rows)
        and metrics["resource_events_reconstructed"] == len(rows)
    )
    report = {
        "schema_version": "sri.experiment.live-agent.codex.v1",
        "experiment": {
            "name": "codex-same-skill-read-only-trials",
            "agent": "codex",
            "agent_version": "0.145.0",
            "model": arguments.model,
            "sandbox": "read-only",
            "ignore_user_config": not arguments.load_user_config,
            "task_sha256": sha256_path(TASK_FILE),
            "skill_sha256": sha256_path(SKILL_FILE),
            "fixture_sha256": _fixture_digest(),
            "limitations": [
                "Three trials are a harness validation, not a stable population estimate.",
                "The task is deterministic and intentionally much smaller than real development work.",
                "Input token counts include Codex runtime context beyond this one Skill.",
            ],
        },
        "metrics": metrics,
        "trials": rows,
        "gate": {"name": "live reconstruction and outcome invariants", "passed": passed},
    }
    output = write_report(EXPERIMENT_DIR, "live-codex", report, arguments.output)
    print(json.dumps({"metrics": metrics, "gate_passed": passed}, indent=2))
    print(f"Report: {output}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

