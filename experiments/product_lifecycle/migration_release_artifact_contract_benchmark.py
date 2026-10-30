#!/usr/bin/env python3
"""Migrate databases created by an identity-verified historical wheel."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_historical_schema_contract_benchmark import (
    _insert_legacy_event,
    _inspect_migrated,
    _schema_contract,
)
from skill_runtime_intelligence.storage import Storage


ARTIFACT_BOOTSTRAP = (
    "import sys\n"
    "from pathlib import Path\n"
    "from skill_runtime_intelligence.storage import Storage\n"
    "storage = Storage(Path(sys.argv[1]))\n"
    "storage.close()\n"
)

VERSION_PROBE = (
    "from importlib.metadata import version\n"
    "print(version('skill-runtime-intelligence'))\n"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def _isolated_subprocess_environment() -> Dict[str, str]:
    environment = dict(os.environ)
    for key in ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV"):
        environment.pop(key, None)
    return environment


def _prepare_artifact_runtime(artifact: Path, environment: Path) -> Path:
    subprocess_environment = _isolated_subprocess_environment()
    subprocess.run(
        [sys.executable, "-m", "venv", str(environment)],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        env=subprocess_environment,
        cwd=environment.parent,
    )
    python = _venv_python(environment)
    subprocess.run(
        [
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-index",
            "--no-deps",
            str(artifact),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        env=subprocess_environment,
        cwd=environment.parent,
    )
    return python


def _bootstrap_artifact_database(python: Path, database: Path) -> None:
    subprocess.run(
        [str(python), "-c", ARTIFACT_BOOTSTRAP, str(database)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=_isolated_subprocess_environment(),
        cwd=database.parent,
    )


def run_benchmark(
    artifact: Path,
    expected_sha256: str,
    expected_version: str,
    trials: int = 3,
    source_url: Optional[str] = None,
    comparison_artifact: Optional[Path] = None,
) -> Dict[str, Any]:
    artifact = artifact.resolve()
    actual_sha256 = _sha256(artifact)
    identity_verified = actual_sha256 == expected_sha256.lower()
    if not identity_verified:
        raise ValueError(
            "artifact SHA-256 does not match the expected release identity"
        )

    comparison = None
    if comparison_artifact is not None:
        comparison_path = comparison_artifact.resolve()
        comparison_sha256 = _sha256(comparison_path)
        comparison = {
            "filename": comparison_path.name,
            "sha256": comparison_sha256,
            "matches_release_digest": comparison_sha256 == actual_sha256,
        }

    evaluations = []
    with tempfile.TemporaryDirectory(
        prefix="sri-release-artifact-contract-"
    ) as directory:
        root = Path(directory)
        python = _prepare_artifact_runtime(artifact, root / "venv")
        installed_version = subprocess.run(
            [str(python), "-c", VERSION_PROBE],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=_isolated_subprocess_environment(),
            cwd=root,
        ).stdout.strip()
        for trial in range(trials):
            database = root / f"artifact-trial-{trial}.db"
            _bootstrap_artifact_database(python, database)
            before = _schema_contract(database)
            _insert_legacy_event(database, f"release-artifact-event-{trial}")
            first = Storage(database)
            first.close()
            second = Storage(database)
            second.close()
            after = _inspect_migrated(database)
            migration_passed = (
                before["provenance_columns_present"] == 0 and after["passed"]
            )
            evaluations.append(
                {
                    "trial": trial,
                    "historical_schema_fingerprint": before["fingerprint"],
                    "migration_passed": migration_passed,
                }
            )

    version_matches = installed_version == expected_version
    migration_passed = sum(
        item["migration_passed"] for item in evaluations
    )
    schema_fingerprints = {
        item["historical_schema_fingerprint"] for item in evaluations
    }
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.release-artifact-contract.v1",
        "experiment": {
            "name": "timestamp-migration-release-artifact-contract",
            "evidence_grade": "Experimental",
            "trials": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "The release wheel creates a controlled database rather than migrating a field database.",
                "One released version, one event shape, and one local platform are covered.",
                "Release metadata availability and download transport are external dependencies.",
                "The current working-tree migrator is not itself installed from a release artifact.",
            ],
        },
        "artifact": {
            "filename": artifact.name,
            "bytes": artifact.stat().st_size,
            "sha256": actual_sha256,
            "expected_sha256": expected_sha256.lower(),
            "identity_verified": identity_verified,
            "source_url": source_url,
            "installed_version": installed_version,
            "expected_version": expected_version,
            "installed_version_matches": version_matches,
            "comparison_artifact": comparison,
        },
        "runtime_isolation": {
            "pythonpath_removed": True,
            "pythonhome_removed": True,
            "virtual_env_hint_removed": True,
            "subprocess_cwd_outside_repository": True,
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
            "evaluations": len(evaluations),
            "passed": migration_passed,
            "failed": len(evaluations) - migration_passed,
            "historical_schema_fingerprints": sorted(schema_fingerprints),
            "legacy_events_preserved_as_unknown": (
                migration_passed == len(evaluations)
            ),
            "idempotent_second_open": migration_passed == len(evaluations),
        },
        "artifact_identity_gate": {
            "name": "digest and installed package version match release identity",
            "passed": identity_verified and version_matches,
        },
        "migration_gate": {
            "name": "release artifact database migrates conservatively",
            "passed": migration_passed == len(evaluations),
        },
        "gate": {
            "name": "verified release identity and conservative migration",
            "passed": (
                identity_verified
                and version_matches
                and migration_passed == len(evaluations)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--expected-version", required=True)
    parser.add_argument("--source-url")
    parser.add_argument("--comparison-artifact", type=Path)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials < 1:
        parser.error("--trials must be >= 1")
    report = run_benchmark(
        artifact=arguments.artifact,
        expected_sha256=arguments.expected_sha256,
        expected_version=arguments.expected_version,
        trials=arguments.trials,
        source_url=arguments.source_url,
        comparison_artifact=arguments.comparison_artifact,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "release-artifact-contract",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "artifact": report["artifact"],
                "environment": report["environment"],
                "metrics": report["metrics"],
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
