#!/usr/bin/env python3
"""Run a randomized 2x2x2x2 Codex Skill-catalog factorial."""

import argparse
import itertools
import json
import random
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
FIXTURE = EXPERIMENT_DIR / "fixture"
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.live_agent.run_catalog_ablation import _expected, _tree_digest


Condition = Tuple[int, str, str, str]


def _description(index: int, length: str, overlap: str) -> str:
    if overlap == "overlap":
        core = (
            f"Validates a bundled fixture payload and returns checksum token {index:03d}; "
            "use for deterministic runtime evidence and verification tasks."
        )
    else:
        core = f"Formats unrelated synthetic calendar category {index:03d}."
    if length == "long":
        core += (
            " It documents selection constraints, input expectations, operational boundaries, "
            "error handling, audit metadata, and reproducible reporting for a controlled catalog study."
        )
    return core


def _prepare(root: Path, block: int, sequence: int, condition: Condition) -> Path:
    cardinality, length, overlap, disclosure = condition
    workspace = root / f"b{block:02d}-s{sequence:02d}"
    shutil.copytree(FIXTURE, workspace)
    skill = workspace / ".agents/skills/checksum-skill"
    instructions = (
        "1. Run `python3 .agents/skills/checksum-skill/scripts/verify.py`.\n"
        "2. Return only the single JSON object printed by the script.\n"
        "3. Do not calculate the checksum yourself and do not modify files.\n"
    )
    if disclosure == "progressive":
        reference = skill / "references/procedure.md"
        reference.write_text("# Procedure\n\n" + instructions, encoding="utf-8")
        body = "Read `references/procedure.md` and follow it exactly.\n"
    else:
        body = instructions
    (skill / "SKILL.md").write_text(
        "---\nname: checksum-skill\n"
        "description: Deterministically validates the bundled fixture payload and returns its token.\n"
        "---\n\n# Checksum Skill\n\n" + body,
        encoding="utf-8",
    )
    root_skills = workspace / ".agents/skills"
    for index in range(cardinality):
        distractor = root_skills / f"distractor-{index:03d}"
        distractor.mkdir(parents=True)
        distractor.joinpath("SKILL.md").write_text(
            "---\n"
            f"name: distractor-{index:03d}\n"
            f"description: {_description(index, length, overlap)}\n"
            "---\n\nThis controlled distractor must not be used for the checksum fixture.\n",
            encoding="utf-8",
        )
    return workspace


def _run(root: Path, block: int, sequence: int, condition: Condition, model: str, timeout: float) -> Dict[str, Any]:
    cardinality, length, overlap, disclosure = condition
    workspace = _prepare(root, block, sequence, condition)
    before = _tree_digest(workspace)
    started = time.perf_counter()
    try:
        process = subprocess.run(
            ["codex", "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check",
             "--ignore-user-config", "--model", model, "-"],
            cwd=workspace,
            input=workspace.joinpath("task.txt").read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        error = ""
    except subprocess.TimeoutExpired:
        return {"block": block, "sequence": sequence, "cardinality": cardinality,
                "description_length": length, "semantic_overlap": overlap,
                "disclosure": disclosure, "status": "timeout", "outcome_verified": False,
                "workspace_unchanged": before == _tree_digest(workspace),
                "wall_ms": (time.perf_counter() - started) * 1000}
    records = []
    for line in process.stdout.splitlines():
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    final = next((r.get("item", {}).get("text", "") for r in reversed(records)
                  if r.get("type") == "item.completed" and r.get("item", {}).get("type") == "agent_message"), "")
    completed = next((r for r in reversed(records) if r.get("type") == "turn.completed"), {})
    commands = [r.get("item", {}).get("command", "") for r in records
                if r.get("item", {}).get("type") == "command_execution"]
    expected = _expected(workspace)
    usage = completed.get("usage") or {}
    return {
        "block": block, "sequence": sequence, "cardinality": cardinality,
        "description_length": length, "semantic_overlap": overlap, "disclosure": disclosure,
        "status": "completed" if process.returncode == 0 else "execution_error",
        "error": error, "exit_code": process.returncode,
        "wall_ms": (time.perf_counter() - started) * 1000,
        "input_tokens": usage.get("input_tokens"), "cached_input_tokens": usage.get("cached_input_tokens"),
        "output_tokens": usage.get("output_tokens"), "outcome_verified": final == expected,
        "workspace_unchanged": before == _tree_digest(workspace),
        "target_skill_loaded": any("checksum-skill/SKILL.md" in c for c in commands),
        "procedure_loaded": any("checksum-skill/references/procedure.md" in c for c in commands),
        "target_script_executed": any("checksum-skill/scripts/verify.py" in c for c in commands),
        "distractor_loaded": any("distractor-" in c and "SKILL.md" in c for c in commands),
    }


def _contrast(rows: Iterable[Dict[str, Any]], factor: str, low: Any, high: Any, field: str) -> Dict[str, Any]:
    usable = [r for r in rows if isinstance(r.get(field), (int, float))]
    left = [r[field] for r in usable if r[factor] == low]
    right = [r[field] for r in usable if r[factor] == high]
    return {"low": low, "high": high, "low_n": len(left), "high_n": len(right),
            "high_minus_low_mean": statistics.mean(right) - statistics.mean(left) if left and right else None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blocks", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.blocks < 2 or args.workers < 1:
        parser.error("at least two blocks and one worker are required")
    conditions: List[Condition] = list(itertools.product(
        (8, 32), ("short", "long"), ("disjoint", "overlap"), ("flat", "progressive")
    ))
    rng = random.Random(args.seed)
    schedule = []
    for block in range(args.blocks):
        order = conditions[:]
        rng.shuffle(order)
        schedule.extend((block, sequence, condition) for sequence, condition in enumerate(order))
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-catalog-factorial-") as directory:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run, Path(directory), b, s, c, args.model, args.timeout_seconds)
                       for b, s, c in schedule]
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda r: (r["block"], r["sequence"]))
    completed = [r for r in rows if r["status"] == "completed"]
    integrity = all(r.get("outcome_verified") and r.get("workspace_unchanged") and
                    r.get("target_skill_loaded") and r.get("target_script_executed") and
                    not r.get("distractor_loaded") and
                    (r["disclosure"] != "progressive" or r.get("procedure_loaded")) for r in completed)
    complete = len(completed) == len(rows)
    contrasts = {}
    for field in ("input_tokens", "wall_ms"):
        contrasts[field] = {
            "cardinality": _contrast(completed, "cardinality", 8, 32, field),
            "description_length": _contrast(completed, "description_length", "short", "long", field),
            "semantic_overlap": _contrast(completed, "semantic_overlap", "disjoint", "overlap", field),
            "disclosure": _contrast(completed, "disclosure", "flat", "progressive", field),
        }
    report = {
        "schema_version": "sri.experiment.catalog-factorial.v1",
        "experiment": {"name": "randomized-balanced-codex-skill-catalog-2x2x2x2",
            "evidence_grade": "Experimental", "model": args.model, "seed": args.seed,
            "blocks": args.blocks, "planned_calls": len(schedule),
            "limitations": ["One installed Agent/model and one machine limit external validity.",
                "Concurrent calls reduce drift but introduce shared-host contention.",
                "Contrasts are descriptive marginal effects for this controlled fixture; they do not establish deployment-wide causality."]},
        "metrics": {"planned_calls": len(rows), "completed_calls": len(completed),
            "verified_calls": sum(bool(r.get("outcome_verified")) for r in completed),
            "integrity_passed": integrity, "main_effect_contrasts": contrasts},
        "rows": rows,
        "gate": {"name": "complete balanced factorial with selection, execution, disclosure, and integrity invariants",
                 "passed": complete and integrity},
    }
    output = write_report(EXPERIMENT_DIR, "catalog-factorial", report, args.output)
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
