#!/usr/bin/env python3
"""Run randomized paired blocks for the Codex Skill catalog ablation."""

import argparse
import json
import random
import statistics
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.live_agent.run_catalog_ablation import _run_condition


def _percentile(values: List[float], probability: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _bootstrap_mean_interval(
    values: List[float], seed: int, samples: int = 10_000
) -> List[float]:
    rng = random.Random(seed)
    means = [
        statistics.mean(rng.choice(values) for _ in values)
        for _ in range(samples)
    ]
    return [_percentile(means, 0.025), _percentile(means, 0.975)]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalogs", default="0,8,32")
    parser.add_argument("--repetitions", type=int, default=4)
    parser.add_argument("--seed", type=int, default=20260801)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    catalogs = sorted({int(item) for item in arguments.catalogs.split(",")})
    if arguments.repetitions < 2:
        parser.error("--repetitions must be at least 2")
    if len(catalogs) < 2 or catalogs[0] < 0:
        parser.error("at least two non-negative catalog sizes are required")
    rng = random.Random(arguments.seed)
    rows: List[Dict[str, Any]] = []
    for block in range(arguments.repetitions):
        order = catalogs[:]
        rng.shuffle(order)
        with tempfile.TemporaryDirectory(prefix=f"sri-catalog-block-{block:02d}-") as directory:
            for sequence, count in enumerate(order):
                row = _run_condition(Path(directory), count, arguments.model)
                row.update({"block": block, "sequence": sequence})
                rows.append(row)
    by_catalog = {}
    for count in catalogs:
        condition = [row for row in rows if row["distractor_skill_count"] == count]
        by_catalog[str(count)] = {
            "trial_count": len(condition),
            "verified_count": sum(row["outcome_verified"] for row in condition),
            "input_tokens_median": statistics.median(row["input_tokens"] for row in condition),
            "input_tokens_min": min(row["input_tokens"] for row in condition),
            "input_tokens_max": max(row["input_tokens"] for row in condition),
            "wall_ms_median": statistics.median(row["wall_ms"] for row in condition),
            "wall_ms_min": min(row["wall_ms"] for row in condition),
            "wall_ms_max": max(row["wall_ms"] for row in condition),
        }
    low, high = catalogs[0], catalogs[-1]
    paired = []
    for block in range(arguments.repetitions):
        block_rows = {row["distractor_skill_count"]: row for row in rows if row["block"] == block}
        paired.append(
            {
                "block": block,
                "high_minus_low_input_tokens": block_rows[high]["input_tokens"] - block_rows[low]["input_tokens"],
                "high_minus_low_wall_ms": block_rows[high]["wall_ms"] - block_rows[low]["wall_ms"],
            }
        )
    token_differences = [row["high_minus_low_input_tokens"] for row in paired]
    wall_differences = [row["high_minus_low_wall_ms"] for row in paired]
    invariants = all(
        row["exit_code"] == 0
        and row["outcome_verified"]
        and row["workspace_unchanged"]
        and row["target_skill_loaded"]
        and row["target_script_executed"]
        and not row["other_skill_loaded"]
        for row in rows
    )
    report = {
        "schema_version": "sri.experiment.catalog-ablation.paired.v1",
        "experiment": {
            "name": "randomized-paired-project-skill-catalog-cardinality",
            "evidence_grade": "Experimental",
            "agent": "codex",
            "model": arguments.model,
            "seed": arguments.seed,
            "repetitions": arguments.repetitions,
            "catalogs": catalogs,
            "limitations": [
                "Blocks ran sequentially on one machine, so time drift remains a covariate.",
                "Synthetic distractors are semantically disjoint and do not estimate overlapping-Skill collisions.",
                "The bootstrap interval describes these blocks and is not a deployment population interval.",
                "Input tokens are Agent-reported totals and include global runtime context.",
            ],
        },
        "condition_summary": by_catalog,
        "paired_endpoint": {
            "low_distractors": low,
            "high_distractors": high,
            "input_token_differences": token_differences,
            "input_token_difference_mean": statistics.mean(token_differences),
            "input_token_difference_bootstrap_95pct": _bootstrap_mean_interval(token_differences, arguments.seed + 1),
            "wall_ms_differences": wall_differences,
            "wall_ms_difference_mean": statistics.mean(wall_differences),
            "wall_ms_difference_bootstrap_95pct": _bootstrap_mean_interval(wall_differences, arguments.seed + 2),
        },
        "rows": sorted(rows, key=lambda row: (row["block"], row["sequence"])),
        "gate": {"name": "paired target-selection, outcome, and integrity invariants", "passed": invariants},
    }
    output = write_report(EXPERIMENT_DIR, "catalog-ablation-paired", report, arguments.output)
    print(json.dumps({"condition_summary": by_catalog, "paired_endpoint": report["paired_endpoint"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if invariants else 1


if __name__ == "__main__":
    raise SystemExit(main())
