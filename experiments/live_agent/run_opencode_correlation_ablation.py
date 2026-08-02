#!/usr/bin/env python3
"""Randomized blocked token-on/off OpenCode non-interference experiment."""

import argparse
import json
import random
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import percentile, write_report
from experiments.live_agent.run_cross_agent_cli_trials import _expected
from experiments.live_agent.run_opencode_attempt_correlation_pilot import _run_trial


def _schedule(pairs: int, seed: int) -> list:
    generator = random.Random(seed)
    rows = []
    trial = 1
    for block in range(1, pairs + 1):
        conditions = ["token_on", "token_off"]
        generator.shuffle(conditions)
        for order, condition in enumerate(conditions, 1):
            rows.append({
                "trial": trial,
                "block": block,
                "order": order,
                "condition": condition,
            })
            trial += 1
    return rows


def _bootstrap_mean_ci(values: list, seed: int, draws: int = 5000) -> list:
    if not values:
        return [None, None]
    generator = random.Random(seed)
    means = []
    for _ in range(draws):
        sample = [generator.choice(values) for _ in values]
        means.append(sum(sample) / len(sample))
    return [percentile(means, 0.025), percentile(means, 0.975)]


def _opencode_counts(database: Path) -> Dict[str, int]:
    connection = sqlite3.connect(database)
    try:
        return {
            "sessions": connection.execute(
                "SELECT COUNT(*) FROM sessions WHERE adapter = 'opencode'"
            ).fetchone()[0],
            "events": connection.execute(
                "SELECT COUNT(*) FROM normalized_events e JOIN sessions s "
                "USING(session_id) WHERE s.adapter = 'opencode'"
            ).fetchone()[0],
            "skill_runs": connection.execute(
                "SELECT COUNT(*) FROM skill_runs WHERE source_adapter = 'opencode'"
            ).fetchone()[0],
        }
    finally:
        connection.close()


def run_experiment(
    pairs: int,
    seed: int,
    model: str,
    timeout_seconds: float,
    database: Path,
) -> Dict[str, Any]:
    if pairs < 2:
        raise ValueError("at least two randomized blocks are required")
    plan = _schedule(pairs, seed)
    expected = _expected()
    collector_before = _opencode_counts(database)
    with tempfile.TemporaryDirectory(prefix="sri-opencode-correlation-ablation-") as root:
        root_path = Path(root)
        trials = []
        for assignment in plan:
            row = _run_trial(
                root_path,
                assignment["trial"],
                model,
                timeout_seconds,
                expected,
                token_enabled=assignment["condition"] == "token_on",
                study_scope="opencode-correlation-ablation-20260731",
            )
            row.update({
                "block": assignment["block"],
                "order": assignment["order"],
            })
            trials.append(row)
    collector_after = _opencode_counts(database)

    groups = {
        condition: [row for row in trials if row["condition"] == condition]
        for condition in ("token_on", "token_off")
    }
    paired_differences = []
    complete_pairs = 0
    for block in range(1, pairs + 1):
        block_rows = {row["condition"]: row for row in trials if row["block"] == block}
        if (
            set(block_rows) == {"token_on", "token_off"}
            and all(row["status"] == "completed" for row in block_rows.values())
        ):
            complete_pairs += 1
            paired_differences.append(
                block_rows["token_on"]["wall_ms"]
                - block_rows["token_off"]["wall_ms"]
            )

    per_condition = {}
    for condition, rows in groups.items():
        walls = [row["wall_ms"] for row in rows if row["status"] == "completed"]
        per_condition[condition] = {
            "planned": len(rows),
            "completed": sum(row["status"] == "completed" for row in rows),
            "verified_outcomes": sum(bool(row.get("outcome_verified")) for row in rows),
            "verified_correlations": sum(
                bool(row.get("correlation_verified")) for row in rows
            ),
            "silent_controls": sum(bool(row.get("control_silent")) for row in rows),
            "raw_token_persistence_findings": sum(
                bool(row.get("raw_token_persisted")) for row in rows
            ),
            "workload_mutations": sum(
                not bool(row.get("workload_unchanged")) for row in rows
            ),
            "wall_p50_ms": percentile(walls, 0.5) if walls else None,
            "wall_p95_ms": percentile(walls, 0.95) if walls else None,
        }

    observed_mean = (
        sum(paired_differences) / len(paired_differences)
        if paired_differences else None
    )
    metrics = {
        "pairs_planned": pairs,
        "complete_pairs": complete_pairs,
        "randomization_seed": seed,
        "per_condition": per_condition,
        "paired_wall_difference_on_minus_off_ms": {
            "mean": observed_mean,
            "median": percentile(paired_differences, 0.5) if paired_differences else None,
            "bootstrap_95_ci": _bootstrap_mean_ci(paired_differences, seed + 1),
            "differences": paired_differences,
        },
        "collector_delta": {
            key: collector_after[key] - collector_before[key]
            for key in collector_before
        },
    }
    token_on = per_condition["token_on"]
    token_off = per_condition["token_off"]
    passed = all([
        complete_pairs == pairs,
        token_on["verified_outcomes"] == pairs,
        token_off["verified_outcomes"] == pairs,
        token_on["verified_correlations"] == pairs,
        token_off["silent_controls"] == pairs,
        token_on["raw_token_persistence_findings"] == 0,
        token_on["workload_mutations"] == 0,
        token_off["workload_mutations"] == 0,
    ])
    return {
        "schema_version": "sri.experiment.opencodelive-correlation-ablation.v1",
        "experiment": {
            "name": "randomized-blocked-opencode-token-on-off",
            "evidence_grade": "Experimental",
            "agent_version": subprocess.run(
                ["opencode", "--version"], capture_output=True, text=True,
                timeout=10,
            ).stdout.strip(),
            "model": model,
            "design": "within-block randomized order; same plugin in both conditions",
            "limitations": [
                "One installed OpenCode system and one local machine were tested.",
                "Model and service latency remain noisy despite randomized order.",
                "The bootstrap interval is descriptive for these blocks only.",
                "Passing non-interference gates does not prove zero overhead.",
            ],
        },
        "metrics": metrics,
        "trials": trials,
        "gate": {
            "name": "Token processing preserves outcomes/workload and emits evidence only when enabled",
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pairs", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--model", default="opencode/deepseek-v4-flash-free")
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--database", type=Path, default=Path(".sri/panorama.db"))
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment(
        arguments.pairs, arguments.seed, arguments.model,
        arguments.timeout_seconds, arguments.database,
    )
    output = write_report(
        EXPERIMENT_DIR, "opencode-correlation-ablation", report,
        arguments.output,
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
