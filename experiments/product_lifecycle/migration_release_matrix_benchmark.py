#!/usr/bin/env python3
"""Run identity and migration gates across a release-wheel manifest."""

import argparse
import json
import os
import platform
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_release_artifact_contract_benchmark import (
    run_benchmark as run_artifact_benchmark,
)


DEFAULT_MANIFEST = EXPERIMENT_DIR / "release_wheel_manifest_v0.1.json"


def run_benchmark(
    manifest_path: Path,
    artifact_directory: Path,
    trials: int = 3,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    for entry in manifest["artifacts"]:
        artifact = artifact_directory / entry["filename"]
        if not artifact.is_file():
            rows.append(
                {
                    "version": entry["version"],
                    "tag": entry["tag"],
                    "status": "not_run",
                    "reason": "artifact_missing",
                    "passed": False,
                }
            )
            continue
        report = run_artifact_benchmark(
            artifact=artifact,
            expected_sha256=entry["sha256"],
            expected_version=entry["version"],
            trials=trials,
            source_url=entry["url"],
        )
        rows.append(
            {
                "version": entry["version"],
                "tag": entry["tag"],
                "status": "completed",
                "artifact_sha256": report["artifact"]["sha256"],
                "installed_version": report["artifact"]["installed_version"],
                "schema_fingerprints": report["metrics"][
                    "historical_schema_fingerprints"
                ],
                "migration_evaluations": report["metrics"]["evaluations"],
                "migration_passed": report["metrics"]["passed"],
                "identity_gate_passed": report["artifact_identity_gate"][
                    "passed"
                ],
                "migration_gate_passed": report["migration_gate"]["passed"],
                "passed": report["gate"]["passed"],
            }
        )

    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    fingerprints = {
        fingerprint
        for row in completed
        for fingerprint in row["schema_fingerprints"]
    }
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.release-wheel-matrix.v1",
        "experiment": {
            "name": "timestamp-migration-release-wheel-matrix",
            "evidence_grade": "Experimental",
            "manifest_evidence_grade": manifest.get("evidence_grade"),
            "manifest_queried_at": manifest.get("queried_at"),
            "release_repository": manifest.get("repository"),
            "trials_per_artifact": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Only wheel artifacts listed in one v0.1 release manifest are covered.",
                "Each artifact creates a controlled database with one event shape.",
                "The current working-tree migrator runs on one local platform.",
                "Missing downloads are not_run rather than migration failures.",
            ],
        },
        "environment": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "logical_cpu_count": os.cpu_count(),
            "load_average_1m": load[0],
            "load_average_5m": load[1],
            "load_average_15m": load[2],
        },
        "metrics": {
            "manifest_artifacts": len(rows),
            "completed_artifacts": len(completed),
            "not_run_artifacts": len(not_run),
            "passed_artifacts": sum(row["passed"] for row in completed),
            "failed_artifacts": sum(not row["passed"] for row in completed),
            "migration_evaluations": sum(
                row["migration_evaluations"] for row in completed
            ),
            "migration_passed": sum(
                row["migration_passed"] for row in completed
            ),
            "distinct_historical_schema_fingerprints": len(fingerprints),
        },
        "artifacts": rows,
        "gate": {
            "name": "all manifest release wheels available, verified, and migrated",
            "passed": (
                len(completed) == len(rows)
                and all(row["passed"] for row in completed)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials < 1:
        parser.error("--trials must be >= 1")
    report = run_benchmark(
        manifest_path=arguments.manifest,
        artifact_directory=arguments.artifact_directory,
        trials=arguments.trials,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "release-wheel-matrix",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
