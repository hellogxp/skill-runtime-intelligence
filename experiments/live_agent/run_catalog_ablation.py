#!/usr/bin/env python3
"""Explore how project Skill catalog size changes a fixed Codex task."""

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
FIXTURE = EXPERIMENT_DIR / "fixture"
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


def _expected(workspace: Path) -> str:
    return subprocess.run(
        [
            sys.executable,
            str(
                workspace
                / ".agents"
                / "skills"
                / "checksum-skill"
                / "scripts"
                / "verify.py"
            ),
        ],
        cwd=workspace,
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()


def _tree_digest(workspace: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(path for path in workspace.rglob("*") if path.is_file()):
        digest.update(str(path.relative_to(workspace)).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _add_distractors(workspace: Path, count: int) -> None:
    root = workspace / ".agents" / "skills"
    for index in range(count):
        skill = root / f"distractor-{index:03d}"
        skill.mkdir(parents=True)
        description = (
            f"Handles unrelated synthetic category {index:03d} for catalog "
            "cardinality experiments; it never validates checksums, payloads, "
            "runtime evidence, fixture tokens, or deterministic script outputs."
        )
        (skill / "SKILL.md").write_text(
            "---\n"
            f"name: distractor-{index:03d}\n"
            f"description: {description}\n"
            "---\n\n"
            "This synthetic Skill is not applicable to the checksum fixture.\n",
            encoding="utf-8",
        )


def _run_condition(root: Path, distractors: int, model: str) -> Dict[str, Any]:
    workspace = root / f"catalog-{distractors:03d}"
    shutil.copytree(FIXTURE, workspace)
    _add_distractors(workspace, distractors)
    before = _tree_digest(workspace)
    command = [
        "codex",
        "exec",
        "--json",
        "--sandbox",
        "read-only",
        "--skip-git-repo-check",
        "--ignore-user-config",
        "--model",
        model,
        "-",
    ]
    started = time.perf_counter()
    process = subprocess.run(
        command,
        cwd=workspace,
        input=(workspace / "task.txt").read_text(encoding="utf-8"),
        capture_output=True,
        text=True,
        timeout=180,
    )
    wall_ms = (time.perf_counter() - started) * 1000
    records = []
    for line in process.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            continue
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
    commands = [
        record.get("item", {}).get("command", "")
        for record in records
        if record.get("item", {}).get("type") == "command_execution"
    ]
    expected = _expected(workspace)
    usage = completed.get("usage", {})
    return {
        "distractor_skill_count": distractors,
        "catalog_skill_count": distractors + 1,
        "exit_code": process.returncode,
        "wall_ms": wall_ms,
        "input_tokens": usage.get("input_tokens"),
        "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"),
        "outcome_verified": final == expected,
        "workspace_unchanged": before == _tree_digest(workspace),
        "target_skill_loaded": any(
            "checksum-skill/SKILL.md" in command for command in commands
        ),
        "target_script_executed": any(
            "checksum-skill/scripts/verify.py" in command for command in commands
        ),
        "other_skill_loaded": any(
            "distractor-" in command and "SKILL.md" in command
            for command in commands
        ),
    }


def _slope(rows: List[Dict[str, Any]], field: str) -> float:
    left, right = rows[0], rows[-1]
    delta_skills = (
        right["distractor_skill_count"] - left["distractor_skill_count"]
    )
    left_value = left.get(field)
    right_value = right.get(field)
    if not delta_skills or not isinstance(left_value, (int, float)):
        return 0.0
    if not isinstance(right_value, (int, float)):
        return 0.0
    return (right_value - left_value) / delta_skills


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogs", default="0,8,32")
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    catalogs = sorted({int(value) for value in arguments.catalogs.split(",")})
    with tempfile.TemporaryDirectory(prefix="sri-catalog-") as directory:
        rows = [
            _run_condition(Path(directory), count, arguments.model)
            for count in catalogs
        ]
    invariant_gate = all(
        row["exit_code"] == 0
        and row["outcome_verified"]
        and row["workspace_unchanged"]
        and row["target_skill_loaded"]
        and row["target_script_executed"]
        and not row["other_skill_loaded"]
        for row in rows
    )
    report = {
        "schema_version": "sri.experiment.catalog-ablation.v1",
        "experiment": {
            "name": "project-skill-catalog-cardinality-exploration",
            "agent": "codex",
            "model": arguments.model,
            "design": "one exploratory trial per catalog size",
            "limitations": [
                "One trial per condition cannot separate catalog effects from runtime variance.",
                "Global runtime context remains present and is not measured independently.",
                "Token slope is exploratory until repeated paired trials are complete.",
            ],
        },
        "metrics": {
            "condition_count": len(rows),
            "verified_conditions": sum(row["outcome_verified"] for row in rows),
            "input_tokens_per_added_skill_endpoint_slope": _slope(
                rows, "input_tokens"
            ),
            "wall_ms_per_added_skill_endpoint_slope": _slope(rows, "wall_ms"),
            "invariant_gate_passed": invariant_gate,
        },
        "conditions": rows,
        "gate": {
            "name": "target selection and execution invariants",
            "passed": invariant_gate,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "catalog-ablation", report, arguments.output
    )
    print(json.dumps({"metrics": report["metrics"], "conditions": rows}, indent=2))
    print(f"Report: {output}")
    return 0 if invariant_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())

