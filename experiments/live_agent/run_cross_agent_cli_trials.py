#!/usr/bin/env python3
"""Run the same deterministic Skill task through three installed Agent CLIs."""

import argparse
import hashlib
import json
import os
import signal
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
FIXTURE = EXPERIMENT_DIR / "cross_agent_fixture"
CANONICAL_SKILL = FIXTURE / "skills" / "checksum-skill"
TASK_FILE = FIXTURE / "task.txt"
QODER_COMMAND = os.environ.get("SRI_QODERCLI", "qodercli")
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import percentile, sha256_path, write_report


AGENT_SKILL_ROOTS = {
    "codex": Path(".agents/skills"),
    "opencode": Path(".opencode/skills"),
    "qoder": Path(".qoder/skills"),
}


def _run_with_process_group(
    command: list,
    stdin: Optional[str],
    timeout_seconds: float,
    environment: Optional[Dict[str, str]] = None,
) -> subprocess.CompletedProcess:
    """Bound a CLI and every descendant that inherits its output pipes."""
    process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE if stdin is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
        env=environment,
    )
    try:
        stdout, stderr = process.communicate(
            input=stdin,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as error:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            process.communicate(timeout=2)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate()
        raise error
    return subprocess.CompletedProcess(
        command,
        process.returncode,
        stdout,
        stderr,
    )


def _version(command: str) -> str:
    try:
        result = subprocess.run(
            [command, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return f"unavailable:{type(error).__name__}"
    return (result.stdout or result.stderr).strip()


def _expected() -> Dict[str, str]:
    result = subprocess.run(
        [sys.executable, str(CANONICAL_SKILL / "scripts" / "verify.py")],
        cwd=FIXTURE,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    return json.loads(result.stdout)


def _tree_manifest(workspace: Path) -> Dict[str, str]:
    manifest = {}
    for path in sorted(item for item in workspace.rglob("*") if item.is_file()):
        if ".git" in path.relative_to(workspace).parts:
            continue
        relative = str(path.relative_to(workspace))
        manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return manifest


def _workload_digest(workspace: Path) -> str:
    """Hash task-owned inputs while excluding per-Agent runtime metadata."""
    digest = hashlib.sha256()
    for relative in (Path("task.txt"), Path("skills")):
        target = workspace / relative
        paths = [target] if target.is_file() else sorted(target.rglob("*"))
        for path in (item for item in paths if item.is_file()):
            digest.update(str(path.relative_to(workspace)).encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _changed_paths(before: Dict[str, str], after: Dict[str, str]) -> list:
    return sorted(
        path for path in set(before) | set(after)
        if before.get(path) != after.get(path)
    )


def _change_summary(before: Dict[str, str], after: Dict[str, str]) -> Dict[str, Any]:
    paths = _changed_paths(before, after)
    roots = sorted({"/".join(Path(path).parts[:2]) for path in paths})
    return {
        "workspace_change_count": len(paths),
        "workspace_change_roots": roots,
        "workspace_change_sample": paths[:20],
    }


def _qoder_authenticated() -> bool:
    try:
        result = subprocess.run(
            [QODER_COMMAND, "status"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and "Account: Not logged in" not in result.stdout


def _workspace(root: Path, agent: str, trial: int) -> Path:
    workspace = root / f"{agent}-trial-{trial:02d}"
    shutil.copytree(FIXTURE, workspace)
    target = workspace / AGENT_SKILL_ROOTS[agent] / "checksum-skill"
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(CANONICAL_SKILL, target)
    subprocess.run(
        ["git", "init", "-q"],
        cwd=workspace,
        check=True,
        timeout=10,
    )
    return workspace


def _walk_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _find_expected(text: str, expected: Dict[str, str]) -> bool:
    candidates = [text]
    try:
        decoded = json.loads(text)
    except json.JSONDecodeError:
        decoded = None
    if decoded is not None:
        candidates.extend(_walk_strings(decoded))
    decoder = json.JSONDecoder()
    for candidate in candidates:
        for index, character in enumerate(candidate):
            if character != "{":
                continue
            try:
                parsed, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if parsed == expected:
                return True
    return False


def _extract_codex(stdout: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
    records = []
    for line in stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    thread_id = next((
        item.get("thread_id") for item in records
        if item.get("type") == "thread.started"
    ), None)
    final = next((
        item.get("item", {}).get("text", "")
        for item in reversed(records)
        if item.get("type") == "item.completed"
        and item.get("item", {}).get("type") == "agent_message"
    ), "")
    usage = next((
        item.get("usage", {}) for item in reversed(records)
        if item.get("type") == "turn.completed"
    ), {})
    return final, thread_id, usage


def _extract_opencode(stdout: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
    texts = []
    session_id = None
    usage: Dict[str, Any] = {}
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = session_id or event.get("sessionID")
        part = event.get("part") or {}
        if event.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
        if event.get("type") == "step_finish":
            usage = dict(part.get("tokens") or {})
    return "".join(texts), session_id, usage


def _extract_qoder(stdout: str) -> Tuple[str, Optional[str], Dict[str, Any]]:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError:
        return stdout, None, {}
    strings = list(_walk_strings(payload))
    session_id = None
    usage: Dict[str, Any] = {}
    if isinstance(payload, dict):
        session_id = payload.get("session_id") or payload.get("sessionId")
        usage = dict(payload.get("usage") or {})
    return "\n".join(strings), session_id, usage


def _command(
    agent: str,
    workspace: Path,
    prompt: str,
    codex_model: str,
    opencode_model: str,
    qoder_model: str,
) -> Tuple[list, Optional[str]]:
    if agent == "codex":
        return ([
            "codex", "exec", "--json", "--sandbox", "read-only",
            "--model", codex_model, "-C", str(workspace), prompt,
        ], None)
    if agent == "opencode":
        return ([
            "opencode", "run", "--format", "json", "--auto",
            "--model", opencode_model, "--dir", str(workspace),
            "--title", "SRI cross-Agent live trial",
        ], prompt)
    return ([
        QODER_COMMAND, "-p", prompt, "-f", "json", "-q", "--allowed-tools",
        "Read,Grep,Glob,Bash", "--max-turns", "8",
        "--model", qoder_model, "-w", str(workspace),
    ], None)


def _run_trial(
    root: Path,
    agent: str,
    trial: int,
    timeout_seconds: float,
    expected: Dict[str, str],
    codex_model: str,
    opencode_model: str,
    qoder_model: str,
) -> Dict[str, Any]:
    workspace = _workspace(root, agent, trial)
    before_manifest = _tree_manifest(workspace)
    before_workload = _workload_digest(workspace)
    prompt = TASK_FILE.read_text(encoding="utf-8")
    command, stdin = _command(
        agent, workspace, prompt, codex_model, opencode_model, qoder_model
    )
    started = time.perf_counter()
    try:
        process = _run_with_process_group(
            command,
            stdin,
            timeout_seconds,
        )
        error = ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        after_manifest = _tree_manifest(workspace)
        return {
            "agent": agent,
            "trial": trial,
            "status": "execution_error",
            "error": type(exc).__name__,
            "wall_ms": (time.perf_counter() - started) * 1000,
            "workload_unchanged": before_workload == _workload_digest(workspace),
            **_change_summary(before_manifest, after_manifest),
        }
    wall_ms = (time.perf_counter() - started) * 1000
    extractor = {
        "codex": _extract_codex,
        "opencode": _extract_opencode,
        "qoder": _extract_qoder,
    }[agent]
    final, session_id, usage = extractor(process.stdout)
    valid = _find_expected(final, expected)
    if process.returncode != 0:
        status = "execution_error"
        error = f"exit_{process.returncode}"
    elif not valid:
        status = "invalid_response"
        error = "expected JSON not found"
    else:
        status = "completed"
    after_manifest = _tree_manifest(workspace)
    return {
        "agent": agent,
        "trial": trial,
        "status": status,
        "error": error,
        "exit_code": process.returncode,
        "wall_ms": wall_ms,
        "outcome_verified": valid,
        "workload_unchanged": before_workload == _workload_digest(workspace),
        **_change_summary(before_manifest, after_manifest),
        "session_id_sha256": (
            hashlib.sha256(str(session_id).encode()).hexdigest()
            if session_id else None
        ),
        "response_sha256": hashlib.sha256(final.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
        "usage": usage,
    }


def _database_counts(database: Path) -> Dict[str, Dict[str, int]]:
    connection = sqlite3.connect(database)
    try:
        sessions = dict(connection.execute(
            "SELECT adapter, COUNT(*) FROM sessions GROUP BY adapter"
        ).fetchall())
        runs = dict(connection.execute(
            "SELECT source_adapter, COUNT(*) FROM skill_runs GROUP BY source_adapter"
        ).fetchall())
        events = dict(connection.execute(
            """
            SELECT s.adapter, COUNT(*)
            FROM normalized_events e JOIN sessions s USING (session_id)
            GROUP BY s.adapter
            """
        ).fetchall())
    finally:
        connection.close()
    return {
        agent: {
            "sessions": int(sessions.get(agent, 0)),
            "skill_runs": int(runs.get(agent, 0)),
            "events": int(events.get(agent, 0)),
        }
        for agent in AGENT_SKILL_ROOTS
    }


def _delta(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    return {
        agent: {
            key: after[agent][key] - before[agent][key]
            for key in before[agent]
        }
        for agent in before
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=4)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument(
        "--agents",
        nargs="+",
        choices=tuple(AGENT_SKILL_ROOTS),
        default=list(AGENT_SKILL_ROOTS),
    )
    parser.add_argument("--timeout-seconds", type=float, default=240)
    parser.add_argument("--database", type=Path, default=Path(".sri/panorama.db"))
    parser.add_argument("--collector-wait-seconds", type=float, default=5)
    parser.add_argument("--codex-model", default="gpt-5.6-sol")
    parser.add_argument(
        "--opencode-model", default="opencode/deepseek-v4-flash-free"
    )
    parser.add_argument("--qoder-model", default="performance")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials <= 0 or arguments.workers <= 0:
        parser.error("--trials and --workers must be positive")

    expected = _expected()
    agent_versions = {
        agent: _version(
            {
                "codex": "codex",
                "opencode": "opencode",
                "qoder": QODER_COMMAND,
            }[agent]
        )
        for agent in arguments.agents
    }
    before_counts = _database_counts(arguments.database)
    rows = []
    qoder_authenticated = _qoder_authenticated()
    with tempfile.TemporaryDirectory(prefix="sri-cross-agent-live-") as directory:
        root = Path(directory)
        with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
            futures = []
            for trial in range(1, arguments.trials + 1):
                for agent in arguments.agents:
                    if agent == "qoder" and not qoder_authenticated:
                        rows.append({
                            "agent": agent,
                            "trial": trial,
                            "status": "precondition_failed",
                            "error": "not_authenticated",
                            "wall_ms": 0.0,
                            "outcome_verified": False,
                            "workload_unchanged": True,
                            "workspace_change_count": 0,
                            "workspace_change_roots": [],
                            "workspace_change_sample": [],
                        })
                        continue
                    futures.append(
                        executor.submit(
                            _run_trial,
                            root,
                            agent,
                            trial,
                            arguments.timeout_seconds,
                            expected,
                            arguments.codex_model,
                            arguments.opencode_model,
                            arguments.qoder_model,
                        )
                    )
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda row: (row["trial"], row["agent"]))
    time.sleep(arguments.collector_wait_seconds)
    after_counts = _database_counts(arguments.database)

    per_agent = {}
    for agent in arguments.agents:
        agent_rows = [row for row in rows if row["agent"] == agent]
        walls = [row["wall_ms"] for row in agent_rows]
        per_agent[agent] = {
            "planned": len(agent_rows),
            "completed": sum(row["status"] == "completed" for row in agent_rows),
            "verified_outcomes": sum(row.get("outcome_verified", False) for row in agent_rows),
            "workload_mutations": sum(not row["workload_unchanged"] for row in agent_rows),
            "runtime_metadata_mutations": sum(
                bool(row["workspace_change_count"]) for row in agent_rows
            ),
            "process_failures": sum(row["status"] == "execution_error" for row in agent_rows),
            "precondition_failures": sum(
                row["status"] == "precondition_failed" for row in agent_rows
            ),
            "invalid_responses": sum(row["status"] == "invalid_response" for row in agent_rows),
            "wall_p50_ms": percentile(walls, 0.5),
            "wall_p95_ms": percentile(walls, 0.95),
        }
    integrity_passed = all(
        row["status"] == "completed" and row["workload_unchanged"]
        for row in rows
    )
    report = {
        "schema_version": "sri.experiment.live-agent.cross-agent-cli.v1",
        "experiment": {
            "name": "cross-agent-same-skill-black-box-cli-pilot",
            "evidence_grade": "Experimental",
            "design": "installed Agent systems, same task and fixture, isolated workspaces, hidden deterministic verifier",
            "agent_versions": agent_versions,
            "models": {
                agent: {
                    "codex": arguments.codex_model,
                    "opencode": arguments.opencode_model,
                    "qoder": arguments.qoder_model,
                }[agent]
                for agent in arguments.agents
            },
            "task_sha256": sha256_path(TASK_FILE),
            "skill_sha256": sha256_path(CANONICAL_SKILL / "SKILL.md"),
            "limitations": [
                "This compares installed Agent systems, not isolated model or scaffold effects.",
                "Four deterministic trials per Agent are a mechanism pilot, not a population estimate.",
                "Different Agent products use different configured model families and runtime context.",
                "Collector deltas establish observed ingestion counts, not exact task-level pairing.",
            ],
        },
        "metrics": {
            "planned_calls": len(rows),
            "completed_calls": sum(row["status"] == "completed" for row in rows),
            "verified_outcomes": sum(row.get("outcome_verified", False) for row in rows),
            "workload_mutations": sum(not row["workload_unchanged"] for row in rows),
            "runtime_metadata_mutations": sum(
                bool(row["workspace_change_count"]) for row in rows
            ),
            "per_agent": per_agent,
            "collector_before": before_counts,
            "collector_after": after_counts,
            "collector_deltas": _delta(before_counts, after_counts),
        },
        "trials": rows,
        "gate": {
            "name": (
                f"{'+'.join(arguments.agents)} deterministic outcome "
                "and workload-integrity"
            ),
            "passed": integrity_passed,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "live-cross-agent-cli", report, arguments.output
    )
    print(json.dumps({
        "metrics": report["metrics"],
        "gate": report["gate"],
    }, indent=2))
    print(f"Report: {output}")
    return 0 if integrity_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
