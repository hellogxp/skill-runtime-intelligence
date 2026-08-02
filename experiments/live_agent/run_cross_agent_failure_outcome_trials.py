#!/usr/bin/env python3
"""Run balanced nonce-bound success and real process-failure Agent trials."""

import argparse
import hashlib
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
FIXTURE = EXPERIMENT_DIR / "failure_outcome_fixture"
CANONICAL_SKILL = FIXTURE / "skills" / "boundary-probe-skill"
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import percentile, sha256_path, write_report
from experiments.live_agent.run_cross_agent_cli_trials import (
    AGENT_SKILL_ROOTS,
    QODER_COMMAND,
    _change_summary,
    _command,
    _database_counts,
    _delta,
    _extract_codex,
    _extract_opencode,
    _extract_qoder,
    _find_expected,
    _qoder_authenticated,
    _run_with_process_group,
    _tree_manifest,
    _version,
    _workload_digest,
)


MODES = ("success", "execution-failure", "resource-failure")


def _expected(mode: str, nonce: str) -> Dict[str, Any]:
    status, boundary, exit_code = {
        "success": ("verified_success", "outcome", 0),
        "execution-failure": ("observed_failure", "execution", 7),
        "resource-failure": ("observed_failure", "resources", 8),
    }[mode]
    token = hashlib.sha256(f"{mode}:{nonce}".encode()).hexdigest()[:20]
    return {
        "status": status,
        "boundary": boundary,
        "exit_code": exit_code,
        "token": f"SRI-{token}",
    }


def _workspace(root: Path, agent: str, trial: int, mode: str) -> Path:
    workspace = root / f"{agent}-{trial:02d}-{mode}"
    shutil.copytree(FIXTURE, workspace)
    target = workspace / AGENT_SKILL_ROOTS[agent] / "boundary-probe-skill"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CANONICAL_SKILL, target)
    command = (
        "python3 skills/boundary-probe-skill/scripts/probe.py "
        f"--mode {mode}"
    )
    (workspace / "task.txt").write_text(
        "Use boundary-probe-skill for this task. Follow it exactly. "
        "Do not read or write outside this repository.\n\n"
        f"Command: `{command}`\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True, timeout=10)
    return workspace


def _run_trial(
    root: Path,
    agent: str,
    trial: int,
    mode: str,
    timeout_seconds: float,
    codex_model: str,
    opencode_model: str,
    qoder_model: str,
) -> Dict[str, Any]:
    nonce = secrets.token_urlsafe(24)
    expected = _expected(mode, nonce)
    workspace = _workspace(root, agent, trial, mode)
    before_manifest = _tree_manifest(workspace)
    before_workload = _workload_digest(workspace)
    prompt = (workspace / "task.txt").read_text(encoding="utf-8")
    command, stdin = _command(
        agent, workspace, prompt, codex_model, opencode_model, qoder_model
    )
    environment = os.environ.copy()
    environment["SRI_TRIAL_NONCE"] = nonce
    started = time.perf_counter()
    try:
        process = _run_with_process_group(
            command,
            stdin,
            timeout_seconds,
            environment=environment,
        )
        error = ""
    except (OSError, subprocess.TimeoutExpired) as exception:
        after = _tree_manifest(workspace)
        return {
            "agent": agent,
            "trial": trial,
            "condition": mode,
            "status": "execution_error",
            "error": type(exception).__name__,
            "wall_ms": (time.perf_counter() - started) * 1000,
            "outcome_verified": False,
            "workload_unchanged": before_workload == _workload_digest(workspace),
            "nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest(),
            **_change_summary(before_manifest, after),
        }
    extractor = {
        "codex": _extract_codex,
        "opencode": _extract_opencode,
        "qoder": _extract_qoder,
    }[agent]
    final, source_session_id, usage = extractor(process.stdout)
    valid = _find_expected(final, expected)
    after = _tree_manifest(workspace)
    return {
        "agent": agent,
        "trial": trial,
        "condition": mode,
        "status": (
            "completed"
            if process.returncode == 0 and valid
            else "invalid_response"
            if process.returncode == 0
            else "execution_error"
        ),
        "error": error if valid else "expected nonce-bound JSON not found",
        "exit_code": process.returncode,
        "wall_ms": (time.perf_counter() - started) * 1000,
        "outcome_verified": valid,
        "expected_process_exit": expected["exit_code"],
        "expected_boundary": expected["boundary"],
        "workload_unchanged": before_workload == _workload_digest(workspace),
        "nonce_sha256": hashlib.sha256(nonce.encode()).hexdigest(),
        "source_session_id_sha256": (
            hashlib.sha256(str(source_session_id).encode()).hexdigest()
            if source_session_id
            else None
        ),
        "response_sha256": hashlib.sha256(final.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
        "usage": usage,
        **_change_summary(before_manifest, after),
    }


def _session_evidence(database: Path, source_digest: str) -> Dict[str, Any]:
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT session_id, source_session_id FROM sessions"
        ).fetchall()
        matches = [
            session_id
            for session_id, source_id in rows
            if source_id
            and hashlib.sha256(str(source_id).encode()).hexdigest() == source_digest
        ]
        if len(matches) != 1:
            return {"session_match_count": len(matches)}
        session_id = matches[0]
        event_rows = connection.execute(
            """
            SELECT event_type, stage, status, evidence_grade, COUNT(*)
            FROM normalized_events
            WHERE session_id = ?
            GROUP BY event_type, stage, status, evidence_grade
            ORDER BY event_type, stage, status, evidence_grade
            """,
            (session_id,),
        ).fetchall()
        return {
            "session_match_count": 1,
            "skill_run_count": int(
                connection.execute(
                    "SELECT COUNT(*) FROM skill_runs WHERE session_id = ?",
                    (session_id,),
                ).fetchone()[0]
            ),
            "explicit_failed_event_count": sum(
                count for _, _, status, _, count in event_rows if status == "failed"
            ),
            "event_signatures": [
                {
                    "event_type": event_type,
                    "stage": stage,
                    "status": status,
                    "evidence_grade": grade,
                    "count": count,
                }
                for event_type, stage, status, grade, count in event_rows
            ],
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials-per-agent", type=int, default=20)
    parser.add_argument("--workers", type=int, default=9)
    parser.add_argument("--agents", nargs="+", choices=tuple(AGENT_SKILL_ROOTS), default=list(AGENT_SKILL_ROOTS))
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--collector-wait-seconds", type=float, default=8)
    parser.add_argument("--database", type=Path, default=Path(".sri/panorama.db"))
    parser.add_argument("--codex-model", default="gpt-5.6-sol")
    parser.add_argument("--opencode-model", default="opencode/deepseek-v4-flash-free")
    parser.add_argument("--qoder-model", default="performance")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials_per_agent < 1 or arguments.workers < 1:
        parser.error("trial and worker counts must be positive")
    versions = {
        agent: _version({"codex": "codex", "opencode": "opencode", "qoder": QODER_COMMAND}[agent])
        for agent in arguments.agents
    }
    qoder_ready = _qoder_authenticated()
    before = _database_counts(arguments.database)
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-balanced-failures-") as directory:
        with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
            futures = []
            for agent in arguments.agents:
                for index in range(arguments.trials_per_agent):
                    trial = index + 1
                    mode = MODES[index % len(MODES)]
                    if agent == "qoder" and not qoder_ready:
                        rows.append({"agent": agent, "trial": trial, "condition": mode, "status": "precondition_failed", "outcome_verified": False, "workload_unchanged": True, "wall_ms": 0.0})
                        continue
                    futures.append(
                        executor.submit(
                            _run_trial,
                            Path(directory),
                            agent,
                            trial,
                            mode,
                            arguments.timeout_seconds,
                            arguments.codex_model,
                            arguments.opencode_model,
                            arguments.qoder_model,
                        )
                    )
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda item: (item["agent"], item["trial"]))
    time.sleep(arguments.collector_wait_seconds)
    for row in rows:
        digest = row.get("source_session_id_sha256")
        row["collector_evidence"] = (
            _session_evidence(arguments.database, digest)
            if digest
            else {"session_match_count": 0}
        )
    after = _database_counts(arguments.database)
    per_agent = {}
    for agent in arguments.agents:
        selected = [item for item in rows if item["agent"] == agent]
        walls = [item["wall_ms"] for item in selected]
        per_agent[agent] = {
            "planned": len(selected),
            "completed": sum(item["status"] == "completed" for item in selected),
            "verified_outcomes": sum(bool(item.get("outcome_verified")) for item in selected),
            "verified_failure_outcomes": sum(bool(item.get("outcome_verified")) and item["condition"] != "success" for item in selected),
            "collector_exact_session_matches": sum(item["collector_evidence"].get("session_match_count") == 1 for item in selected),
            "collector_explicit_failure_runs": sum(item["collector_evidence"].get("explicit_failed_event_count", 0) > 0 for item in selected),
            "workload_mutations": sum(not item["workload_unchanged"] for item in selected),
            "wall_p50_ms": percentile(walls, 0.5),
            "wall_p95_ms": percentile(walls, 0.95),
        }
    gate_passed = all(
        item["status"] == "completed"
        and item["outcome_verified"]
        and item["workload_unchanged"]
        for item in rows
    )
    report = {
        "schema_version": "sri.experiment.cross-agent-balanced-failure-outcome.v1",
        "experiment": {
            "name": "installed-agent-balanced-real-process-failure-and-verified-outcome",
            "evidence_grade": "Experimental",
            "agent_versions": versions,
            "models": {"codex": arguments.codex_model, "opencode": arguments.opencode_model, "qoder": arguments.qoder_model},
            "skill_sha256": sha256_path(CANONICAL_SKILL / "SKILL.md"),
            "trials_per_agent": arguments.trials_per_agent,
            "condition_schedule": list(MODES),
            "limitations": [
                "Failures are controlled real non-zero processes in isolated fixtures, not naturally occurring production incidents.",
                "A nonce-bound verifier proves the returned result came from runtime access; it does not prove hidden model reasoning.",
                "Different installed Agent systems use different models and scaffolds.",
                "Collector session matching is exact by source-session digest; absent matches remain unresolved.",
            ],
        },
        "metrics": {
            "planned_calls": len(rows),
            "completed_calls": sum(item["status"] == "completed" for item in rows),
            "verified_outcomes": sum(bool(item.get("outcome_verified")) for item in rows),
            "per_agent": per_agent,
            "collector_before": before,
            "collector_after": after,
            "collector_deltas": _delta(before, after),
        },
        "trials": rows,
        "gate": {"name": "balanced nonce-bound outcome and workload integrity", "passed": gate_passed},
    }
    output = write_report(EXPERIMENT_DIR, "balanced-failure-outcome", report, arguments.output)
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
