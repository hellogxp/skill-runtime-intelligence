#!/usr/bin/env python3
"""Audit stable, scoped, and fail-closed privacy-safe host identity."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.privacy_safe_host_identity import (
    SCHEME,
    scoped_host_alias,
)


def _worker(identity_path: Path, scope: str) -> int:
    print(json.dumps(scoped_host_alias(identity_path, scope)))
    return 0


def _concurrent_aliases(
    identity_path: Path,
    scope: str,
    workers: int,
) -> list:
    processes = [
        subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--worker",
                str(identity_path),
                scope,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(workers)
    ]
    rows = []
    for process in processes:
        stdout, stderr = process.communicate(timeout=30)
        if process.returncode != 0:
            raise RuntimeError(stderr.strip() or "host identity worker failed")
        rows.append(json.loads(stdout))
    return rows


def _expect_failure(identity_path: Path, scope: str) -> Dict[str, Any]:
    before = identity_path.read_bytes() if identity_path.exists() else b""
    try:
        scoped_host_alias(identity_path, scope)
        failure_type = "none"
    except (OSError, ValueError) as exc:
        failure_type = type(exc).__name__
    after = identity_path.read_bytes() if identity_path.exists() else b""
    return {
        "failure_type": failure_type,
        "failed_closed": failure_type != "none" and before == after,
        "bytes_unchanged": before == after,
    }


def run_benchmark(
    trials: int = 3,
    workers: int = 8,
) -> Dict[str, Any]:
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-host-identity-contract-"
    ) as directory:
        root = Path(directory)
        for trial in range(trials):
            trial_root = root / f"trial-{trial}"
            identity_path = trial_root / "host.secret"
            scope_a = f"paper-experiment-{trial}"
            scope_b = f"support-export-{trial}"
            concurrent = _concurrent_aliases(
                identity_path,
                scope_a,
                workers,
            )
            alias_a = scoped_host_alias(identity_path, scope_a)
            alias_b = scoped_host_alias(identity_path, scope_b)
            local_secret = identity_path.read_text(encoding="ascii").strip()
            export_payload = json.dumps(
                {
                    "same_scope": concurrent,
                    "scope_a": alias_a,
                    "scope_b": alias_b,
                },
                sort_keys=True,
            )

            corrupt = trial_root / "corrupt.secret"
            corrupt.write_text("not-a-uuid\n", encoding="ascii")
            corrupt.chmod(0o600)
            corrupt_result = _expect_failure(corrupt, scope_a)

            permissive = trial_root / "permissive.secret"
            permissive.write_text(f"{local_secret}\n", encoding="ascii")
            permissive.chmod(0o644)
            permission_result = _expect_failure(permissive, scope_a)

            symlink = trial_root / "symlink.secret"
            symlink.symlink_to(identity_path)
            symlink_result = _expect_failure(symlink, scope_a)

            aliases = {item["host_alias"] for item in concurrent}
            rows.append(
                {
                    "trial": trial,
                    "workers": workers,
                    "same_scope_alias_count": len(aliases),
                    "same_scope_stable": (
                        len(aliases) == 1
                        and alias_a["host_alias"] in aliases
                    ),
                    "cross_scope_distinct": (
                        alias_a["host_alias"] != alias_b["host_alias"]
                    ),
                    "identity_mode": oct(identity_path.stat().st_mode & 0o777),
                    "permissions_private": (
                        identity_path.stat().st_mode & 0o077 == 0
                    ),
                    "secret_absent_from_export": (
                        local_secret not in export_payload
                    ),
                    "corrupt_identity": corrupt_result,
                    "permissive_identity": permission_result,
                    "symlink_identity": symlink_result,
                    "passed": (
                        len(aliases) == 1
                        and alias_a["host_alias"] in aliases
                        and alias_a["host_alias"] != alias_b["host_alias"]
                        and identity_path.stat().st_mode & 0o077 == 0
                        and local_secret not in export_payload
                        and corrupt_result["failed_closed"]
                        and permission_result["failed_closed"]
                        and symlink_result["failed_closed"]
                    ),
                }
            )
    report = {
        "schema_version": "sri.experiment.host-identity-contract.v1",
        "experiment": {
            "name": "privacy-safe-scoped-host-identity-contract",
            "evidence_grade": "Experimental",
            "trials": trials,
            "workers_per_trial": workers,
            "limitations": [
                "All trials run on one filesystem and operating system.",
                "Scope-specific aliases reduce linkability but are still identifiers within a scope.",
                "The experiment does not test secret backup, user consent, or rotation UX.",
                "Passing this contract does not retroactively identify earlier reports.",
            ],
        },
        "identity_contract": {
            "scheme": SCHEME,
            "local_origin": "random UUIDv4 secret",
            "export_derivation": "HMAC-SHA256(secret, scope), truncated to 128 bits",
            "forbidden_inputs": [
                "hostname",
                "hardware serial",
                "MAC address",
                "username",
            ],
        },
        "metrics": {
            "trials": trials,
            "worker_initializations": trials * workers,
            "passed_trials": sum(row["passed"] for row in rows),
            "stable_same_scope_trials": sum(
                row["same_scope_stable"] for row in rows
            ),
            "distinct_cross_scope_trials": sum(
                row["cross_scope_distinct"] for row in rows
            ),
            "private_permission_trials": sum(
                row["permissions_private"] for row in rows
            ),
            "redacted_export_trials": sum(
                row["secret_absent_from_export"] for row in rows
            ),
            "corrupt_fail_closed_trials": sum(
                row["corrupt_identity"]["failed_closed"] for row in rows
            ),
            "permissive_fail_closed_trials": sum(
                row["permissive_identity"]["failed_closed"] for row in rows
            ),
            "symlink_fail_closed_trials": sum(
                row["symlink_identity"]["failed_closed"] for row in rows
            ),
        },
        "trials": rows,
        "gate": {
            "name": "stable scoped host identity without local-secret export",
            "passed": len(rows) == trials and all(row["passed"] for row in rows),
        },
    }
    return report


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--worker":
        return _worker(Path(sys.argv[2]), sys.argv[3])
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(arguments.trials, arguments.workers)
    output = write_report(
        EXPERIMENT_DIR,
        "host-identity-contract",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
