#!/usr/bin/env python3
"""Audit an explicit, privacy-safe cross-Agent paired-task key contract."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.privacy_safe_paired_task_key import (
    ASSIGNMENT_SCHEMA,
    SCHEME,
    paired_task_key,
)


AGENTS = ("codex", "qoder", "opencode")


def _assignment(
    task_id: str,
    *,
    scope: str,
    protocol: str,
) -> Dict[str, str]:
    return {
        "schema_version": ASSIGNMENT_SCHEMA,
        "study_scope": scope,
        "protocol_version": protocol,
        "task_id": task_id,
    }


def _expect_failure(
    secret_path: Path,
    assignment: Dict[str, Any],
) -> Dict[str, Any]:
    before = secret_path.read_bytes() if secret_path.exists() else b""
    try:
        paired_task_key(secret_path, assignment)
        failure_type = "none"
    except (OSError, ValueError) as exc:
        failure_type = type(exc).__name__
    after = secret_path.read_bytes() if secret_path.exists() else b""
    return {
        "failure_type": failure_type,
        "failed_closed": failure_type != "none" and before == after,
        "bytes_unchanged": before == after,
    }


def run_benchmark(
    trials: int = 5,
    task_pool_size: int = 128,
) -> Dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-paired-task-key-contract-"
    ) as directory:
        root = Path(directory)
        for trial in range(trials):
            trial_root = root / f"trial-{trial}"
            secret_path = trial_root / "study.secret"
            scope = f"paper-study-{trial}"
            protocol = "cross-agent-v1"
            task_id = f"opaque-task-{trial}"
            base_assignment = _assignment(
                task_id,
                scope=scope,
                protocol=protocol,
            )
            agent_outputs = [
                paired_task_key(secret_path, dict(base_assignment))
                for _agent in AGENTS
            ]
            base_key = agent_outputs[0]["task_key"]
            different_task = paired_task_key(
                secret_path,
                _assignment(
                    f"{task_id}-variant",
                    scope=scope,
                    protocol=protocol,
                ),
            )
            different_scope = paired_task_key(
                secret_path,
                _assignment(
                    task_id,
                    scope=f"{scope}-support",
                    protocol=protocol,
                ),
            )
            different_protocol = paired_task_key(
                secret_path,
                _assignment(
                    task_id,
                    scope=scope,
                    protocol=f"{protocol}-revision",
                ),
            )
            pool_keys = {
                paired_task_key(
                    secret_path,
                    _assignment(
                        f"pool-task-{trial}-{index}",
                        scope=scope,
                        protocol=protocol,
                    ),
                )["task_key"]
                for index in range(task_pool_size)
            }
            local_secret = secret_path.read_text(encoding="ascii").strip()
            export_payload = json.dumps(
                {
                    "same_assignment": agent_outputs,
                    "different_task": different_task,
                    "different_scope": different_scope,
                    "different_protocol": different_protocol,
                },
                sort_keys=True,
            )

            missing_task = dict(base_assignment)
            del missing_task["task_id"]
            missing_task_result = _expect_failure(
                secret_path,
                missing_task,
            )
            prompt_only = dict(base_assignment)
            del prompt_only["task_id"]
            prompt_only["prompt"] = "raw task content must not be inferred"
            prompt_only_result = _expect_failure(
                secret_path,
                prompt_only,
            )

            corrupt = trial_root / "corrupt.secret"
            corrupt.parent.mkdir(parents=True, exist_ok=True)
            corrupt.write_text("not-hex\n", encoding="ascii")
            corrupt.chmod(0o600)
            corrupt_result = _expect_failure(corrupt, base_assignment)

            permissive = trial_root / "permissive.secret"
            permissive.write_text(f"{local_secret}\n", encoding="ascii")
            permissive.chmod(0o644)
            permissive_result = _expect_failure(
                permissive,
                base_assignment,
            )

            symlink = trial_root / "symlink.secret"
            symlink.symlink_to(secret_path)
            symlink_result = _expect_failure(symlink, base_assignment)

            same_assignment_converged = (
                len({row["task_key"] for row in agent_outputs}) == 1
            )
            variants = {
                base_key,
                different_task["task_key"],
                different_scope["task_key"],
                different_protocol["task_key"],
            }
            row = {
                "trial": trial,
                "agent_derivations": len(agent_outputs),
                "same_assignment_converged": same_assignment_converged,
                "cross_task_distinct": (
                    different_task["task_key"] != base_key
                ),
                "cross_scope_distinct": (
                    different_scope["task_key"] != base_key
                ),
                "cross_protocol_distinct": (
                    different_protocol["task_key"] != base_key
                ),
                "all_domain_variants_distinct": len(variants) == 4,
                "task_pool_size": task_pool_size,
                "task_pool_collision_free": (
                    len(pool_keys) == task_pool_size
                ),
                "secret_mode": oct(secret_path.stat().st_mode & 0o777),
                "permissions_private": (
                    secret_path.stat().st_mode & 0o077 == 0
                ),
                "secret_absent_from_export": (
                    local_secret not in export_payload
                ),
                "task_id_absent_from_export": task_id not in export_payload,
                "missing_task": missing_task_result,
                "prompt_only": prompt_only_result,
                "corrupt_secret": corrupt_result,
                "permissive_secret": permissive_result,
                "symlink_secret": symlink_result,
            }
            row["passed"] = all(
                [
                    row["same_assignment_converged"],
                    row["cross_task_distinct"],
                    row["cross_scope_distinct"],
                    row["cross_protocol_distinct"],
                    row["all_domain_variants_distinct"],
                    row["task_pool_collision_free"],
                    row["permissions_private"],
                    row["secret_absent_from_export"],
                    row["task_id_absent_from_export"],
                    row["missing_task"]["failed_closed"],
                    row["prompt_only"]["failed_closed"],
                    row["corrupt_secret"]["failed_closed"],
                    row["permissive_secret"]["failed_closed"],
                    row["symlink_secret"]["failed_closed"],
                ]
            )
            rows.append(row)

    metric_names = [
        "same_assignment_converged",
        "cross_task_distinct",
        "cross_scope_distinct",
        "cross_protocol_distinct",
        "all_domain_variants_distinct",
        "task_pool_collision_free",
        "permissions_private",
        "secret_absent_from_export",
        "task_id_absent_from_export",
    ]
    metrics = {
        "trials": trials,
        "agent_derivations": trials * len(AGENTS),
        "task_keys_generated": trials * (task_pool_size + 4),
        "passed_trials": sum(row["passed"] for row in rows),
        **{
            f"{name}_trials": sum(row[name] for row in rows)
            for name in metric_names
        },
        "missing_task_fail_closed_trials": sum(
            row["missing_task"]["failed_closed"] for row in rows
        ),
        "prompt_only_fail_closed_trials": sum(
            row["prompt_only"]["failed_closed"] for row in rows
        ),
        "corrupt_secret_fail_closed_trials": sum(
            row["corrupt_secret"]["failed_closed"] for row in rows
        ),
        "permissive_secret_fail_closed_trials": sum(
            row["permissive_secret"]["failed_closed"] for row in rows
        ),
        "symlink_secret_fail_closed_trials": sum(
            row["symlink_secret"]["failed_closed"] for row in rows
        ),
    }
    report = {
        "schema_version": "sri.experiment.paired-task-key-contract.v1",
        "experiment": {
            "name": "privacy-safe-explicit-paired-task-key-contract",
            "evidence_grade": "Experimental",
            "trials": trials,
            "agents_per_trial": len(AGENTS),
            "task_pool_size": task_pool_size,
            "limitations": [
                "Assignments and Agent names are synthetic.",
                "The mechanism proves explicit assignment identity, not semantic task equivalence.",
                "Study-secret distribution, rotation, consent, and recovery UX are untested.",
                "The experiment runs on one local filesystem and does not integrate the key into production SkillRun storage.",
                "Collision-free synthetic samples do not prove cryptographic collision impossibility.",
            ],
        },
        "contract": {
            "assignment_schema": ASSIGNMENT_SCHEMA,
            "scheme": SCHEME,
            "secret_origin": "random 256-bit study secret",
            "derivation": (
                "HMAC-SHA256(secret, length-prefixed study scope, "
                "protocol version, and opaque explicit task ID), "
                "truncated to 128 bits"
            ),
            "agent_identity_in_derivation": False,
            "raw_prompt_in_derivation": False,
            "semantic_similarity_in_derivation": False,
            "time_proximity_in_derivation": False,
        },
        "metrics": metrics,
        "trials": rows,
        "gate": {
            "name": (
                "explicit paired-task identity is stable, scoped, private, "
                "and fail-closed"
            ),
            "passed": len(rows) == trials and all(row["passed"] for row in rows),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--task-pool-size", type=int, default=128)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(arguments.trials, arguments.task_pool_size)
    output = write_report(
        EXPERIMENT_DIR,
        "paired-task-key-contract",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
