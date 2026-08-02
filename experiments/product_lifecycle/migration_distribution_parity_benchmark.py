#!/usr/bin/env python3
"""Compare release wheel and sdist schema/migration contracts."""

import argparse
import email
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_historical_schema_contract_benchmark import (
    HISTORICAL_BOOTSTRAP,
    _insert_legacy_event,
    _inspect_migrated,
    _schema_contract,
)
from experiments.product_lifecycle.migration_release_artifact_contract_benchmark import (
    _isolated_subprocess_environment,
    _sha256,
    run_benchmark as run_wheel_benchmark,
)
from skill_runtime_intelligence.storage import Storage


DEFAULT_WHEEL_MANIFEST = EXPERIMENT_DIR / "release_wheel_manifest_v0.1.json"
DEFAULT_SDIST_MANIFEST = EXPERIMENT_DIR / "release_sdist_manifest_v0.1.json"


def _safe_extract(archive: Path, destination: Path) -> Path:
    with tarfile.open(archive, mode="r:gz") as bundle:
        destination_root = destination.resolve()
        members = bundle.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise ValueError("sdist contains an unsafe path")
        bundle.extractall(destination)
    roots = {
        member.name.split("/", 1)[0]
        for member in members
        if member.name and member.name != "."
    }
    if len(roots) != 1:
        raise ValueError("sdist must contain exactly one root directory")
    return destination / next(iter(roots))


def _sdist_metadata(source_root: Path) -> Dict[str, str]:
    metadata_path = source_root / "PKG-INFO"
    parsed = email.message_from_string(
        metadata_path.read_text(encoding="utf-8")
    )
    return {
        "name": str(parsed["Name"]),
        "version": str(parsed["Version"]),
    }


def _bootstrap_sdist_database(source_root: Path, database: Path) -> str:
    environment = _isolated_subprocess_environment()
    environment["PYTHONPATH"] = str(source_root / "src")
    probe = (
        "from skill_runtime_intelligence import storage\n"
        "print(storage.__file__)\n"
    )
    imported_path = subprocess.run(
        [sys.executable, "-c", probe],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
        cwd=database.parent,
    ).stdout.strip()
    resolved_import = Path(imported_path).resolve()
    if source_root.resolve() not in resolved_import.parents:
        raise ValueError("sdist runtime resolved outside the extracted artifact")
    subprocess.run(
        [sys.executable, "-c", HISTORICAL_BOOTSTRAP, str(database)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
        env=environment,
        cwd=database.parent,
    )
    return str(resolved_import.relative_to(source_root.resolve()))


def _run_sdist_contract(
    artifact: Path,
    expected_sha256: str,
    expected_version: str,
    trials: int,
    root: Path,
) -> Dict[str, Any]:
    actual_sha256 = _sha256(artifact)
    identity_verified = actual_sha256 == expected_sha256
    if not identity_verified:
        raise ValueError("sdist SHA-256 does not match release identity")
    source_root = _safe_extract(artifact, root / "source")
    metadata = _sdist_metadata(source_root)
    version_matches = metadata["version"] == expected_version
    evaluations = []
    imported_module = None
    for trial in range(trials):
        database = root / f"sdist-{trial}.db"
        imported_module = _bootstrap_sdist_database(source_root, database)
        before = _schema_contract(database)
        _insert_legacy_event(database, f"sdist-event-{trial}")
        first = Storage(database)
        first.close()
        second = Storage(database)
        second.close()
        after = _inspect_migrated(database)
        evaluations.append(
            {
                "schema_fingerprint": before["fingerprint"],
                "migration_passed": (
                    before["provenance_columns_present"] == 0
                    and after["passed"]
                ),
            }
        )
    migration_passed = sum(row["migration_passed"] for row in evaluations)
    return {
        "sha256": actual_sha256,
        "identity_verified": identity_verified,
        "metadata_version": metadata["version"],
        "version_matches": version_matches,
        "imported_module": imported_module,
        "schema_fingerprints": sorted(
            {row["schema_fingerprint"] for row in evaluations}
        ),
        "migration_evaluations": len(evaluations),
        "migration_passed": migration_passed,
        "passed": (
            identity_verified
            and version_matches
            and migration_passed == len(evaluations)
        ),
    }


def _by_version(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["version"]: row for row in manifest["artifacts"]}


def run_benchmark(
    wheel_manifest_path: Path,
    sdist_manifest_path: Path,
    artifact_directory: Path,
    trials: int = 3,
) -> Dict[str, Any]:
    wheel_manifest = json.loads(
        wheel_manifest_path.read_text(encoding="utf-8")
    )
    sdist_manifest = json.loads(
        sdist_manifest_path.read_text(encoding="utf-8")
    )
    wheels = _by_version(wheel_manifest)
    sdists = _by_version(sdist_manifest)
    versions = sorted(set(wheels) | set(sdists))
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-distribution-parity-"
    ) as directory:
        root = Path(directory)
        for version in versions:
            if version not in wheels or version not in sdists:
                rows.append(
                    {
                        "version": version,
                        "status": "not_run",
                        "reason": "manifest_pair_missing",
                        "passed": False,
                    }
                )
                continue
            wheel_entry = wheels[version]
            sdist_entry = sdists[version]
            wheel_path = artifact_directory / wheel_entry["filename"]
            sdist_path = artifact_directory / sdist_entry["filename"]
            if not wheel_path.is_file() or not sdist_path.is_file():
                rows.append(
                    {
                        "version": version,
                        "status": "not_run",
                        "reason": "artifact_pair_missing",
                        "wheel_available": wheel_path.is_file(),
                        "sdist_available": sdist_path.is_file(),
                        "passed": False,
                    }
                )
                continue
            wheel = run_wheel_benchmark(
                artifact=wheel_path,
                expected_sha256=wheel_entry["sha256"],
                expected_version=version,
                trials=trials,
                source_url=wheel_entry["url"],
            )
            sdist = _run_sdist_contract(
                artifact=sdist_path,
                expected_sha256=sdist_entry["sha256"],
                expected_version=version,
                trials=trials,
                root=root / version,
            )
            wheel_fingerprints = wheel["metrics"][
                "historical_schema_fingerprints"
            ]
            schema_parity = (
                wheel_fingerprints == sdist["schema_fingerprints"]
            )
            passed = wheel["gate"]["passed"] and sdist["passed"] and schema_parity
            rows.append(
                {
                    "version": version,
                    "status": "completed",
                    "wheel_sha256": wheel["artifact"]["sha256"],
                    "sdist_sha256": sdist["sha256"],
                    "wheel_version": wheel["artifact"]["installed_version"],
                    "sdist_version": sdist["metadata_version"],
                    "wheel_schema_fingerprints": wheel_fingerprints,
                    "sdist_schema_fingerprints": sdist[
                        "schema_fingerprints"
                    ],
                    "schema_parity": schema_parity,
                    "wheel_migration_evaluations": wheel["metrics"][
                        "evaluations"
                    ],
                    "sdist_migration_evaluations": sdist[
                        "migration_evaluations"
                    ],
                    "wheel_migration_passed": wheel["metrics"]["passed"],
                    "sdist_migration_passed": sdist["migration_passed"],
                    "passed": passed,
                }
            )

    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.distribution-parity.v1",
        "experiment": {
            "name": "release-wheel-sdist-schema-parity",
            "evidence_grade": "Experimental",
            "versions": versions,
            "trials_per_distribution": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Only v0.1 release artifacts and one controlled event shape are covered.",
                "The sdist source tree is executed directly rather than built into a wheel.",
                "The current working-tree migrator runs on one local platform.",
                "Schema parity does not imply complete runtime behavior parity.",
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
            "version_pairs": len(rows),
            "completed_pairs": len(completed),
            "not_run_pairs": len(not_run),
            "passed_pairs": sum(row["passed"] for row in completed),
            "failed_pairs": sum(not row["passed"] for row in completed),
            "schema_parity_pairs": sum(
                row["schema_parity"] for row in completed
            ),
            "migration_evaluations": sum(
                row["wheel_migration_evaluations"]
                + row["sdist_migration_evaluations"]
                for row in completed
            ),
            "migration_passed": sum(
                row["wheel_migration_passed"]
                + row["sdist_migration_passed"]
                for row in completed
            ),
        },
        "pairs": rows,
        "gate": {
            "name": "all release wheel/sdist pairs verified and schema-equivalent",
            "passed": (
                len(completed) == len(rows)
                and all(row["passed"] for row in completed)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel-manifest",
        type=Path,
        default=DEFAULT_WHEEL_MANIFEST,
    )
    parser.add_argument(
        "--sdist-manifest",
        type=Path,
        default=DEFAULT_SDIST_MANIFEST,
    )
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials < 1:
        parser.error("--trials must be >= 1")
    report = run_benchmark(
        wheel_manifest_path=arguments.wheel_manifest,
        sdist_manifest_path=arguments.sdist_manifest,
        artifact_directory=arguments.artifact_directory,
        trials=arguments.trials,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "distribution-parity",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
