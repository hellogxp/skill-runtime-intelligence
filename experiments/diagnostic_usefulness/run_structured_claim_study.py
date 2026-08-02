#!/usr/bin/env python3
"""Run structured-only claim classification in fresh model sessions."""

import argparse
import hashlib
import json
import random
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.run_claim_output_mode_study import (
    _invoke,
    _prompt,
)
from skill_runtime_intelligence.diagnostics import validate_causal_claim


def run(
    cases_path: Path,
    model: str,
    seed: int,
    workers: int,
    timeout_seconds: float,
) -> dict:
    cases = load_jsonl(cases_path)
    cli_version = subprocess.run(
        ["opencode", "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    trials = []
    for case in cases:
        expected = validate_causal_claim(
            case["causal_scope"], case["expected_claim_kind"]
        )
        if expected["allowed"] != case["expected_allowed"]:
            raise ValueError(f"{case['case_id']}: invalid expected policy")
        prompt = _prompt(case, "structured")
        trials.append(
            {
                "case_id": case["case_id"],
                "mode": "structured",
                "causal_scope": case["causal_scope"],
                "expected_claim_kind": case["expected_claim_kind"],
                "expected_allowed": case["expected_allowed"],
                "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
                "prompt": prompt,
            }
        )
    random.Random(seed).shuffle(trials)
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            executor.submit(
                _invoke,
                dict(trial),
                model,
                cli_version,
                timeout_seconds,
            )
            for trial in trials
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: row["case_id"])
    completed = [row for row in rows if row["status"] == "completed"]
    metrics = {
        "planned": len(rows),
        "completed": len(completed),
        "response_completion_rate": (
            len(completed) / len(rows) if rows else 0.0
        ),
        "claim_kind_correct": sum(
            row["claim_kind_correct"] for row in completed
        ),
        "guard_decision_correct": sum(
            row["guard_decision_correct"] for row in completed
        ),
        "false_allows": sum(row["false_allow"] for row in completed),
        "false_denies": sum(row["false_deny"] for row in completed),
        "input_tokens": sum(
            int(row.get("usage", {}).get("input", 0))
            for row in completed
        ),
        "total_tokens": sum(
            int(row.get("usage", {}).get("total", 0))
            for row in completed
        ),
    }
    return {
        "schema_version": "sri.experiment.claim-output-mode-study.v1",
        "experiment": {
            "name": "structured-only-claim-study",
            "evidence_grade": "experimental",
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "model": model,
            "model_cli": "opencode",
            "model_cli_version": cli_version,
            "seed": seed,
            "session_policy": (
                "fresh pure session per trial; stdin prompt; isolated "
                "temporary XDG state"
            ),
            "modes": ["structured"],
            "limitations": [
                "The corpus is small and hand-authored.",
                "One response per model and case does not estimate repeated-run variance.",
                "The recorded model ID does not independently verify model-family identity.",
            ],
        },
        "metrics": {"structured": metrics},
        "trials": rows,
        "gates": {
            "response_completion": metrics["response_completion_rate"] >= 0.9,
            "no_false_allow": metrics["false_allows"] == 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    parser.add_argument("--model", required=True)
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run(
        arguments.cases,
        arguments.model,
        arguments.seed,
        arguments.workers,
        arguments.timeout_seconds,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "structured-claim-study",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
