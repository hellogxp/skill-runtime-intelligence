#!/usr/bin/env python3
"""Run controlled multi-step Skills over frozen snapshots of real repositories."""

import argparse
import hashlib
import json
import os
import random
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
PROFILE_MANIFEST = EXPERIMENT_DIR / "multirepo_profiles.json"
PROBE = EXPERIMENT_DIR / "probe.py"
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
)


FAULT_MODES = (
    "clean",
    "instructions_failure",
    "resource_missing",
    "execution_failure",
    "artifact_corruption",
    "outcome_unverified",
    "verifier_conflict",
)


def _default_repositories() -> Dict[str, Path]:
    configured_root = os.environ.get("SRI_BENCHMARK_ROOT")
    root = Path(configured_root).expanduser().resolve() if configured_root else Path.home()
    return {
        "tinylru": root / "tinylru",
        "rapid-tele": root / "rapid" / "rapid-tele",
        "llm-mi": root / "llm-mi",
        "llm-mechanistic-interpretability": root / "llm-mechanistic-interpretability",
        "hello-skill": root / "hello-skill",
        "rapid-agent": root / "rapid" / "RAPID-Agent",
    }


def _parse_repository_overrides(values: Iterable[str]) -> Dict[str, Path]:
    repositories = _default_repositories()
    for value in values:
        if "=" not in value:
            raise ValueError("repository overrides must use KEY=/absolute/path")
        key, path = value.split("=", 1)
        repositories[key] = Path(path).expanduser().resolve()
    return repositories


def _git(repository: Path, *arguments: str, text: bool = True):
    result = subprocess.run(["git", "-C", str(repository), *arguments], capture_output=True,
                            text=text, check=True, timeout=30)
    return result.stdout


def _load_sources(manifest: Path, repositories: Dict[str, Path]):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    sources = {}
    for profile in payload["profiles"]:
        repository = repositories[profile["repo_key"]]
        revision = _git(repository, "rev-parse", "HEAD").strip()
        dirty_count = len(_git(repository, "status", "--short").splitlines())
        files = {}
        digest = hashlib.sha256()
        for relative in profile["files"]:
            content = _git(repository, "show", f"{revision}:{relative}", text=False)
            files[relative] = content
            digest.update(relative.encode())
            digest.update(b"\0")
            digest.update(content)
            digest.update(b"\0")
        sources[profile["repo_key"]] = {
            "profile": profile,
            "revision": revision,
            "source_dirty_path_count": dirty_count,
            "source_digest": digest.hexdigest(),
            "files": files,
        }
    return payload, sources


def _skill_body(profile: Dict[str, Any]) -> str:
    return (
        "---\n"
        f"name: {profile['skill_id']}\n"
        f"description: {profile['description']}\n"
        "---\n\n"
        f"# {profile['skill_id']}\n\n"
        "This controlled audit operates on the frozen real-repository snapshot in `repository/`.\n\n"
        "1. Read `profile.json` to identify the three repository inputs.\n"
        f"2. Run `python3 skills/{profile['skill_id']}/scripts/probe.py`.\n"
        "3. The probe checks instructions, resources, execution, artifact integrity, and outcome verification in order.\n"
        "4. Return only the single JSON object printed by the probe, even when the command exits non-zero.\n"
        "5. Do not modify the repository snapshot or any task-owned file.\n"
    )


def _materialize(root: Path, source: Dict[str, Any], agent: str, sequence: int, mode: str) -> Path:
    profile = source["profile"]
    workspace = root / f"{agent}-{sequence:03d}-{profile['repo_key']}-{mode}"
    repository = workspace / "repository"
    repository.mkdir(parents=True)
    for relative, content in source["files"].items():
        path = repository / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    canonical = workspace / "skills" / profile["skill_id"]
    canonical.joinpath("scripts").mkdir(parents=True)
    canonical.joinpath("SKILL.md").write_text(_skill_body(profile), encoding="utf-8")
    canonical.joinpath("scripts/probe.py").write_bytes(PROBE.read_bytes())
    canonical.joinpath("profile.json").write_text(json.dumps({
        "repo_key": profile["repo_key"], "skill_id": profile["skill_id"],
        "files": profile["files"], "source_digest": source["source_digest"]},
        sort_keys=True), encoding="utf-8")
    target = workspace / AGENT_SKILL_ROOTS[agent] / profile["skill_id"]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(canonical, target)
    faults = workspace / "faults"
    faults.mkdir()
    if mode == "resource_missing":
        (repository / profile["files"][-1]).unlink()
    if mode == "execution_failure":
        faults.joinpath("execution.json").write_text("{invalid-json", encoding="utf-8")
    if mode == "artifact_corruption":
        faults.joinpath("artifact-digest.txt").write_text("corrupt", encoding="utf-8")
    if mode == "verifier_conflict":
        faults.joinpath("verifier.txt").write_text("failed", encoding="utf-8")
    command = f"python3 skills/{profile['skill_id']}/scripts/probe.py"
    workspace.joinpath("task.txt").write_text(
        f"Use the {profile['skill_id']} Skill to audit this frozen repository snapshot. "
        "Follow its instructions exactly. Do not read or write outside this workspace.\n\n"
        f"Required command: `{command}`\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True, timeout=10)
    return workspace


def _task_digest(workspace: Path) -> str:
    digest = hashlib.sha256()
    for root in ("repository", "skills", "faults"):
        for path in sorted(workspace.joinpath(root).rglob("*")):
            if path.is_file():
                digest.update(str(path.relative_to(workspace)).encode())
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
    return digest.hexdigest()


def _oracle(workspace: Path, mode: str, nonce: str):
    environment = os.environ.copy()
    environment.update({"SRI_FAULT_MODE": mode, "SRI_TRIAL_NONCE": nonce})
    process = subprocess.run(
        [sys.executable, str(next(workspace.glob("skills/*/scripts/probe.py")))],
        cwd=workspace, env=environment, capture_output=True, text=True, timeout=15)
    result = json.loads(process.stdout)
    if process.returncode != result["exit_code"]:
        raise RuntimeError("oracle exit code does not match emitted result")
    return result


def _source_strings(stdout: str):
    strings = []
    for line in stdout.splitlines():
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        stack = [item]
        while stack:
            value = stack.pop()
            if isinstance(value, str):
                strings.append(value)
            elif isinstance(value, dict):
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)
    return strings


def _session_evidence(database: Path, source_digest: str):
    connection = sqlite3.connect(database)
    try:
        matches = [session_id for session_id, source_id in connection.execute(
            "SELECT session_id, source_session_id FROM sessions").fetchall()
            if source_id and hashlib.sha256(str(source_id).encode()).hexdigest() == source_digest]
        if len(matches) != 1:
            return {"session_match_count": len(matches)}
        session_id = matches[0]
        rows = connection.execute(
            "SELECT event_type, stage, status, evidence_grade, COUNT(*) FROM normalized_events "
            "WHERE session_id=? GROUP BY event_type,stage,status,evidence_grade "
            "ORDER BY event_type,stage,status,evidence_grade", (session_id,)).fetchall()
        return {"session_match_count": 1,
                "skill_run_count": connection.execute("SELECT COUNT(*) FROM skill_runs WHERE session_id=?", (session_id,)).fetchone()[0],
                "explicit_failed_event_count": sum(count for _, _, status, _, count in rows if status == "failed"),
                "event_signatures": [{"event_type": event_type, "stage": stage, "status": status,
                                      "evidence_grade": grade, "count": count}
                                     for event_type, stage, status, grade, count in rows]}
    finally:
        connection.close()


def _run_trial(root, source, agent, sequence, mode, timeout, models):
    nonce = secrets.token_urlsafe(24)
    workspace = _materialize(root, source, agent, sequence, mode)
    expected = _oracle(workspace, mode, nonce)
    before_tree = _tree_manifest(workspace)
    before_task = _task_digest(workspace)
    prompt = workspace.joinpath("task.txt").read_text(encoding="utf-8")
    command, stdin = _command(agent, workspace, prompt, models["codex"], models["opencode"], models["qoder"])
    environment = os.environ.copy()
    environment.update({"SRI_FAULT_MODE": mode, "SRI_TRIAL_NONCE": nonce})
    started = time.perf_counter()
    try:
        process = _run_with_process_group(command, stdin, timeout, environment=environment)
    except (OSError, subprocess.TimeoutExpired) as error:
        after = _tree_manifest(workspace)
        return {"agent": agent, "repo_key": source["profile"]["repo_key"],
                "skill_id": source["profile"]["skill_id"], "sequence": sequence,
                "source_revision": source["revision"], "source_digest": source["source_digest"],
                "fault_mode": mode, "gold_boundary": expected["boundary"],
                "gold_reported_status": expected["reported_status"],
                "gold_verifier_status": expected["verifier_status"], "gold_trace": expected["trace"],
                "oracle_exit_code": expected["exit_code"], "status": "execution_error",
                "error": type(error).__name__, "outcome_verified": False,
                "workload_unchanged": before_task == _task_digest(workspace),
                "wall_ms": (time.perf_counter() - started) * 1000,
                **_change_summary(before_tree, after)}
    extractor = {"codex": _extract_codex, "opencode": _extract_opencode, "qoder": _extract_qoder}[agent]
    final, source_session_id, usage = extractor(process.stdout)
    valid = _find_expected(final, expected)
    strings = _source_strings(process.stdout)
    after = _tree_manifest(workspace)
    session_digest = hashlib.sha256(str(source_session_id).encode()).hexdigest() if source_session_id else None
    return {"agent": agent, "repo_key": source["profile"]["repo_key"],
            "source_revision": source["revision"], "source_digest": source["source_digest"],
            "skill_id": source["profile"]["skill_id"], "sequence": sequence, "fault_mode": mode,
            "gold_boundary": expected["boundary"], "gold_reported_status": expected["reported_status"],
            "gold_verifier_status": expected["verifier_status"], "gold_trace": expected["trace"],
            "oracle_exit_code": expected["exit_code"],
            "status": "completed" if process.returncode == 0 and valid else "invalid_response" if process.returncode == 0 else "execution_error",
            "error": "" if valid else "nonce-bound oracle JSON not found", "agent_exit_code": process.returncode,
            "outcome_verified": valid, "workload_unchanged": before_task == _task_digest(workspace),
            "target_skill_loaded": any(f"{source['profile']['skill_id']}/SKILL.md" in item for item in strings),
            "target_probe_executed": any(f"{source['profile']['skill_id']}/scripts/probe.py" in item for item in strings),
            "wall_ms": (time.perf_counter() - started) * 1000, "usage": usage,
            "source_session_id_sha256": session_digest,
            "response_sha256": hashlib.sha256(final.encode()).hexdigest(),
            "stderr_sha256": hashlib.sha256(process.stderr.encode()).hexdigest(),
            **_change_summary(before_tree, after)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profiles", type=Path, default=PROFILE_MANIFEST)
    parser.add_argument("--profile-keys", default="", help="Optional comma-separated repository keys")
    parser.add_argument("--repo", action="append", default=[], help="Override KEY=/absolute/path")
    parser.add_argument("--agents", nargs="+", choices=tuple(AGENT_SKILL_ROOTS), default=list(AGENT_SKILL_ROOTS))
    parser.add_argument("--fault-modes", default=",".join(FAULT_MODES))
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--collector-wait-seconds", type=float, default=15)
    parser.add_argument("--database", type=Path, default=Path(".sri/panorama.db"))
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--codex-model", default="gpt-5.6-sol")
    parser.add_argument("--opencode-model", default="opencode/deepseek-v4-flash-free")
    parser.add_argument("--qoder-model", default="performance")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repetitions < 1 or args.workers < 1:
        parser.error("repetitions and workers must be positive")
    modes = tuple(item for item in args.fault_modes.split(",") if item)
    if not modes or not set(modes) <= set(FAULT_MODES):
        parser.error("fault modes must be a non-empty subset of the frozen modes")
    repositories = _parse_repository_overrides(args.repo)
    profile_manifest, sources = _load_sources(args.profiles, repositories)
    if args.profile_keys:
        selected_keys = {item for item in args.profile_keys.split(",") if item}
        unknown = selected_keys - set(sources)
        if unknown:
            parser.error(f"unknown profile keys: {sorted(unknown)}")
        sources = {key: value for key, value in sources.items() if key in selected_keys}
    models = {"codex": args.codex_model, "opencode": args.opencode_model, "qoder": args.qoder_model}
    versions = {agent: _version({"codex": "codex", "opencode": "opencode", "qoder": QODER_COMMAND}[agent]) for agent in args.agents}
    qoder_ready = _qoder_authenticated()
    schedule = []
    rng = random.Random(args.seed)
    for agent in args.agents:
        cells = [(source, mode, repetition) for source in sources.values() for mode in modes for repetition in range(args.repetitions)]
        rng.shuffle(cells)
        schedule.extend((agent, index + 1, source, mode, repetition) for index, (source, mode, repetition) in enumerate(cells))
    before = _database_counts(args.database)
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-multirepo-") as directory:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = []
            for agent, sequence, source, mode, repetition in schedule:
                if agent == "qoder" and not qoder_ready:
                    rows.append({"agent": agent, "repo_key": source["profile"]["repo_key"],
                                 "skill_id": source["profile"]["skill_id"], "sequence": sequence,
                                 "fault_mode": mode, "repetition": repetition, "status": "precondition_failed",
                                 "outcome_verified": False, "workload_unchanged": True, "wall_ms": 0.0})
                else:
                    futures.append(executor.submit(_run_trial, Path(directory), source, agent, sequence, mode,
                                                   args.timeout_seconds, models))
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda row: (row["agent"], row["sequence"]))
    time.sleep(args.collector_wait_seconds)
    for row in rows:
        digest = row.get("source_session_id_sha256")
        row["collector_evidence"] = _session_evidence(args.database, digest) if digest else {"session_match_count": 0}
    after = _database_counts(args.database)
    per_agent = {}
    for agent in args.agents:
        selected = [row for row in rows if row["agent"] == agent]
        walls = [row["wall_ms"] for row in selected]
        per_agent[agent] = {"planned": len(selected), "completed": sum(row["status"] == "completed" for row in selected),
                            "verified": sum(bool(row.get("outcome_verified")) for row in selected),
                            "exact_session_matches": sum(row["collector_evidence"].get("session_match_count") == 1 for row in selected),
                            "skill_runs": sum(row["collector_evidence"].get("skill_run_count", 0) for row in selected),
                            "explicit_failure_sessions": sum(row["collector_evidence"].get("explicit_failed_event_count", 0) > 0 for row in selected),
                            "workload_mutations": sum(not row.get("workload_unchanged", False) for row in selected),
                            "wall_p50_ms": percentile(walls, 0.5), "wall_p95_ms": percentile(walls, 0.95)}
    matrix_integrity = (
        len(rows) == len(schedule)
        and all(row.get("workload_unchanged") for row in rows)
        and all(row.get("collector_evidence", {}).get("session_match_count") == 1
                for row in rows if row.get("status") != "precondition_failed")
        and not any(row.get("status") == "precondition_failed" for row in rows)
    )
    source_manifest = [{"repo_key": source["profile"]["repo_key"], "skill_id": source["profile"]["skill_id"],
                        "revision": source["revision"], "source_digest": source["source_digest"],
                        "file_count": len(source["files"]), "source_dirty_path_count": source["source_dirty_path_count"]}
                       for source in sources.values()]
    report = {"schema_version": "sri.experiment.multirepo-agent-benchmark.v1",
              "experiment": {"name": "frozen-real-repository-multistep-skill-fault-matrix", "evidence_grade": "Experimental",
                 "profile_manifest_sha256": sha256_path(args.profiles), "probe_sha256": sha256_path(PROBE),
                 "seed": args.seed, "agents": args.agents, "agent_versions": versions, "models": models,
                 "fault_modes": list(modes), "repetitions": args.repetitions, "source_manifest": source_manifest,
                 "limitations": ["Repository bytes come from real frozen commits, but the audit Skills and faults are controlled experiment overlays.",
                    "A nonce-bound response proves runtime access, not hidden model reasoning.",
                    "Fault ground truth comes from the injected manifest and deterministic probe; it is not a production-incident prevalence sample.",
                    "Installed Agents use different models and scaffolds, so cross-Agent differences are system-level observations."]},
              "metrics": {"planned_calls": len(rows), "completed_calls": sum(row["status"] == "completed" for row in rows),
                          "verified_calls": sum(bool(row.get("outcome_verified")) for row in rows),
                          "per_agent": per_agent, "collector_before": before, "collector_after": after,
                          "collector_deltas": _delta(before, after)},
              "rows": rows,
              "gate": {"name": "all matrix cells launched, read-only, and exactly collector-correlated", "passed": matrix_integrity},
              "response_gate": {"name": "all Agents return exact nonce-bound oracle JSON",
                                "passed": all(row.get("outcome_verified") for row in rows)}}
    output = write_report(EXPERIMENT_DIR, "multirepo-agent-benchmark", report, args.output)
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if matrix_integrity else 1


if __name__ == "__main__":
    raise SystemExit(main())
