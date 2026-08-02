#!/usr/bin/env python3
"""Run a real OpenCode hook pilot for privacy-safe attempt late binding."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
PLUGIN = EXPERIMENT_DIR / "correlation_plugin" / "skill-runtime-correlation.js"
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import percentile, write_report
from experiments.live_agent.run_cross_agent_cli_trials import (
    CANONICAL_SKILL,
    TASK_FILE,
    _expected,
    _extract_opencode,
    _find_expected,
    _tree_manifest,
    _workload_digest,
    _workspace,
)
from experiments.privacy_safe_attempt_correlation import (
    CORRELATION_SCHEMA,
    attempt_correlation_token,
)


def _read_evidence(path: Path) -> list:
    records = []
    if not path.exists():
        return records
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def _files_contain(root: Path, needle: str) -> bool:
    encoded = needle.encode("ascii")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        try:
            if encoded in path.read_bytes():
                return True
        except OSError:
            continue
    return False


def _run_trial(
    root: Path,
    trial: int,
    model: str,
    timeout_seconds: float,
    expected: Dict[str, str],
    token_enabled: bool = True,
    study_scope: str = "opencode-live-correlation-pilot-20260731",
) -> Dict[str, Any]:
    workspace = _workspace(root, "opencode", trial)
    plugin_target = workspace / ".opencode/plugins" / PLUGIN.name
    plugin_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(PLUGIN, plugin_target)
    before_manifest = _tree_manifest(workspace)
    before_workload = _workload_digest(workspace)
    token_record = (
        attempt_correlation_token(
            root / "study.secret",
            {
                "schema_version": CORRELATION_SCHEMA,
                "study_scope": study_scope,
                "adapter": "opencode",
                "attempt_nonce": f"trial-{trial}",
            },
        ) if token_enabled else None
    )
    evidence_path = root / f"trial-{trial:02d}-evidence.jsonl"
    environment = dict(os.environ)
    environment["SRI_ATTEMPT_CORRELATION_EVIDENCE"] = str(evidence_path)
    if token_record:
        environment["SRI_ATTEMPT_CORRELATION_TOKEN"] = token_record["token"]
    command = [
        "opencode", "run", "--format", "json", "--auto", "--model", model,
        "--dir", str(workspace), "--title", "SRI attempt correlation pilot",
    ]
    started = time.perf_counter()
    try:
        process = subprocess.run(
            command,
            input=TASK_FILE.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            env=environment,
            timeout=timeout_seconds,
        )
        execution_error = "" if process.returncode == 0 else f"exit_{process.returncode}"
    except (OSError, subprocess.TimeoutExpired) as error:
        return {
            "trial": trial,
            "status": "execution_error",
            "error": type(error).__name__,
            "wall_ms": (time.perf_counter() - started) * 1000,
            "workload_unchanged": before_workload == _workload_digest(workspace),
        }
    wall_ms = (time.perf_counter() - started) * 1000
    final, session_id, usage = _extract_opencode(process.stdout)
    evidence = _read_evidence(evidence_path)
    token_matches = [
        record.get("token_sha256") == token_record["token_sha256"]
        for record in evidence
    ] if token_record else []
    evidence_session_hashes = {
        hashlib.sha256(str(record.get("session_id", "")).encode()).hexdigest()
        for record in evidence if record.get("session_id")
    }
    output_session_hash = (
        hashlib.sha256(str(session_id).encode()).hexdigest() if session_id else None
    )
    raw_persisted = bool(token_record and (
        token_record["token"] in process.stdout
        or token_record["token"] in process.stderr
        or _files_contain(workspace, token_record["token"])
        or (
            evidence_path.exists()
            and token_record["token"].encode("ascii") in evidence_path.read_bytes()
        )
    ))
    after_manifest = _tree_manifest(workspace)
    changed_paths = sorted(
        path for path in set(before_manifest) | set(after_manifest)
        if before_manifest.get(path) != after_manifest.get(path)
    )
    verified = _find_expected(final, expected)
    correlated = bool(token_record and (
        session_id and evidence and all(token_matches)
        and evidence_session_hashes == {output_session_hash}
    ))
    control_silent = not token_record and not evidence
    contract_ok = correlated if token_record else control_silent
    return {
        "trial": trial,
        "condition": "token_on" if token_record else "token_off",
        "status": (
            "completed" if not execution_error and verified and contract_ok
            and not raw_persisted else "contract_failed"
        ),
        "error": execution_error,
        "exit_code": process.returncode,
        "wall_ms": wall_ms,
        "outcome_verified": verified,
        "correlation_verified": correlated,
        "control_silent": control_silent,
        "evidence_event_count": len(evidence),
        "evidence_event_types": sorted({
            str(record.get("event_type", "")) for record in evidence
        }),
        "unique_evidence_sessions": len(evidence_session_hashes),
        "raw_token_persisted": raw_persisted,
        "workload_unchanged": before_workload == _workload_digest(workspace),
        "runtime_change_roots": sorted({
            "/".join(Path(path).parts[:2]) for path in changed_paths
        }),
        "usage": usage,
    }


def run_pilot(trials: int, model: str, timeout_seconds: float) -> Dict[str, Any]:
    expected = _expected()
    with tempfile.TemporaryDirectory(prefix="sri-opencode-correlation-live-") as root:
        root_path = Path(root)
        rows = [
            _run_trial(root_path, trial, model, timeout_seconds, expected)
            for trial in range(1, trials + 1)
        ]
    completed = [row for row in rows if row["status"] == "completed"]
    wall_times = [row["wall_ms"] for row in completed]
    metrics = {
        "planned_trials": trials,
        "completed_contract_trials": len(completed),
        "verified_outcomes": sum(bool(row.get("outcome_verified")) for row in rows),
        "verified_correlations": sum(bool(row.get("correlation_verified")) for row in rows),
        "raw_token_persistence_findings": sum(
            bool(row.get("raw_token_persisted")) for row in rows
        ),
        "workload_mutations": sum(
            not bool(row.get("workload_unchanged")) for row in rows
        ),
        "wall_p50_ms": percentile(wall_times, 0.5) if wall_times else None,
        "wall_p95_ms": percentile(wall_times, 0.95) if wall_times else None,
    }
    passed = all([
        len(completed) == trials,
        metrics["verified_outcomes"] == trials,
        metrics["verified_correlations"] == trials,
        metrics["raw_token_persistence_findings"] == 0,
        metrics["workload_mutations"] == 0,
    ])
    return {
        "schema_version": "sri.experiment.opencodelive-attempt-correlation.v1",
        "experiment": {
            "name": "opencode-official-hook-attempt-correlation-live-pilot",
            "evidence_grade": "Experimental",
            "agent_version": subprocess.run(
                ["opencode", "--version"], capture_output=True, text=True,
                timeout=10,
            ).stdout.strip(),
            "model": model,
            "skill_sha256": hashlib.sha256(
                CANONICAL_SKILL.joinpath("SKILL.md").read_bytes()
            ).hexdigest(),
            "limitations": [
                "This is one installed OpenCode system on one local machine.",
                "The project hook is Experimental instrumentation, not product rollout.",
                "No no-token randomized control was run in this pilot.",
                "Successful correlation does not establish Skill or outcome causality.",
            ],
        },
        "metrics": metrics,
        "trials": rows,
        "gate": {
            "name": "OpenCode propagates an attempt token to official hook evidence without raw persistence",
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--model", default="opencode/deepseek-v4-flash-free")
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_pilot(arguments.trials, arguments.model, arguments.timeout_seconds)
    output = write_report(
        EXPERIMENT_DIR, "opencode-attempt-correlation-live", report,
        arguments.output,
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
