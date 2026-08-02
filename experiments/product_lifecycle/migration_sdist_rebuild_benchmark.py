#!/usr/bin/env python3
"""Compare offline sdist rebuilds with published release wheels."""

import argparse
import email
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import zipfile
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_distribution_parity_benchmark import (
    DEFAULT_SDIST_MANIFEST,
    DEFAULT_WHEEL_MANIFEST,
)
from experiments.product_lifecycle.migration_release_artifact_contract_benchmark import (
    _isolated_subprocess_environment,
    _sha256,
    run_benchmark as run_wheel_benchmark,
)


def _by_version(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["version"]: row for row in manifest["artifacts"]}


def _wheel_contract(path: Path) -> Dict[str, Any]:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        metadata_names = [
            name for name in names if name.endswith(".dist-info/METADATA")
        ]
        entry_point_names = [
            name
            for name in names
            if name.endswith(".dist-info/entry_points.txt")
        ]
        wheel_names = [
            name for name in names if name.endswith(".dist-info/WHEEL")
        ]
        if len(metadata_names) != 1 or len(wheel_names) != 1:
            raise ValueError("wheel metadata layout is ambiguous")
        metadata = email.message_from_bytes(
            archive.read(metadata_names[0])
        )
        wheel_metadata = email.message_from_bytes(
            archive.read(wheel_names[0])
        )
        entry_points = (
            archive.read(entry_point_names[0]).decode("utf-8").strip()
            if len(entry_point_names) == 1
            else ""
        )
    return {
        "name": str(metadata["Name"]),
        "version": str(metadata["Version"]),
        "requires_python": str(metadata.get("Requires-Python", "")),
        "entry_points": entry_points,
        "wheel_tags": sorted(wheel_metadata.get_all("Tag", [])),
    }


def _build_wheel(
    sdist: Path,
    output: Path,
    source_date_epoch: str = "",
    python_executable: Path = Path(sys.executable),
) -> Path:
    output.mkdir(parents=True)
    environment = _isolated_subprocess_environment()
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    if source_date_epoch:
        environment["SOURCE_DATE_EPOCH"] = source_date_epoch
    subprocess.run(
        [
            str(python_executable),
            "-m",
            "pip",
            "wheel",
            "--no-cache-dir",
            "--no-index",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(output),
            str(sdist),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
        env=environment,
        cwd=output,
    )
    wheels = list(output.glob("*.whl"))
    if len(wheels) != 1:
        raise ValueError("sdist rebuild did not produce exactly one wheel")
    return wheels[0]


def run_benchmark(
    wheel_manifest_path: Path,
    sdist_manifest_path: Path,
    artifact_directory: Path,
    migration_trials: int = 1,
    build_repetitions: int = 2,
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
        prefix="sri-sdist-rebuild-"
    ) as directory:
        root = Path(directory)
        for version in versions:
            wheel_entry = wheels.get(version)
            sdist_entry = sdists.get(version)
            if wheel_entry is None or sdist_entry is None:
                rows.append(
                    {
                        "version": version,
                        "status": "not_run",
                        "reason": "manifest_pair_missing",
                        "passed": False,
                    }
                )
                continue
            release_wheel = artifact_directory / wheel_entry["filename"]
            sdist = artifact_directory / sdist_entry["filename"]
            if not release_wheel.is_file() or not sdist.is_file():
                rows.append(
                    {
                        "version": version,
                        "status": "not_run",
                        "reason": "artifact_pair_missing",
                        "passed": False,
                    }
                )
                continue
            release_identity = (
                _sha256(release_wheel) == wheel_entry["sha256"]
            )
            sdist_identity = _sha256(sdist) == sdist_entry["sha256"]
            if not release_identity or not sdist_identity:
                raise ValueError("release artifact digest mismatch")

            rebuilt_wheels = [
                _build_wheel(sdist, root / version / f"build-{index}")
                for index in range(build_repetitions)
            ]
            rebuilt_digests = [_sha256(path) for path in rebuilt_wheels]
            release_contract = _wheel_contract(release_wheel)
            rebuilt_contract = _wheel_contract(rebuilt_wheels[0])
            contract_parity = release_contract == rebuilt_contract

            release_migration = run_wheel_benchmark(
                artifact=release_wheel,
                expected_sha256=wheel_entry["sha256"],
                expected_version=version,
                trials=migration_trials,
                source_url=wheel_entry["url"],
            )
            rebuilt_migration = run_wheel_benchmark(
                artifact=rebuilt_wheels[0],
                expected_sha256=rebuilt_digests[0],
                expected_version=version,
                trials=migration_trials,
                source_url=f"offline-rebuild:{sdist_entry['filename']}",
            )
            release_fingerprints = release_migration["metrics"][
                "historical_schema_fingerprints"
            ]
            rebuilt_fingerprints = rebuilt_migration["metrics"][
                "historical_schema_fingerprints"
            ]
            schema_parity = release_fingerprints == rebuilt_fingerprints
            repeated_build_digest_match = (
                len(set(rebuilt_digests)) == 1
                if build_repetitions > 1
                else None
            )
            rebuilt_matches_release_digest = (
                rebuilt_digests[0] == wheel_entry["sha256"]
            )
            passed = (
                release_identity
                and sdist_identity
                and contract_parity
                and schema_parity
                and release_migration["gate"]["passed"]
                and rebuilt_migration["gate"]["passed"]
            )
            rows.append(
                {
                    "version": version,
                    "status": "completed",
                    "release_wheel_sha256": wheel_entry["sha256"],
                    "sdist_sha256": sdist_entry["sha256"],
                    "rebuilt_wheel_sha256": rebuilt_digests[0],
                    "rebuilt_matches_release_digest": (
                        rebuilt_matches_release_digest
                    ),
                    "repeated_build_digest_match": (
                        repeated_build_digest_match
                    ),
                    "metadata_cli_contract_parity": contract_parity,
                    "schema_parity": schema_parity,
                    "release_schema_fingerprints": release_fingerprints,
                    "rebuilt_schema_fingerprints": rebuilt_fingerprints,
                    "migration_evaluations": (
                        release_migration["metrics"]["evaluations"]
                        + rebuilt_migration["metrics"]["evaluations"]
                    ),
                    "migration_passed": (
                        release_migration["metrics"]["passed"]
                        + rebuilt_migration["metrics"]["passed"]
                    ),
                    "passed": passed,
                }
            )

    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    repeated_rows = [
        row
        for row in completed
        if row["repeated_build_digest_match"] is not None
    ]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.sdist-rebuild-parity.v1",
        "experiment": {
            "name": "offline-sdist-rebuild-release-wheel-parity",
            "evidence_grade": "Experimental",
            "migration_trials_per_wheel": migration_trials,
            "build_repetitions": build_repetitions,
            "build_network_disabled": True,
            "build_isolation_disabled": True,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "One local Python, setuptools, wheel, and pip toolchain is used.",
                "No-build-isolation uses recorded host build dependencies.",
                "Contract parity covers selected metadata, CLI entry points, wheel tags, and schema.",
                "Byte mismatch is diagnostic and is not itself a contract failure.",
            ],
        },
        "build_environment": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "pip_version": package_version("pip"),
            "setuptools_version": package_version("setuptools"),
            "wheel_version": package_version("wheel"),
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
            "metadata_cli_contract_parity_pairs": sum(
                row["metadata_cli_contract_parity"] for row in completed
            ),
            "schema_parity_pairs": sum(
                row["schema_parity"] for row in completed
            ),
            "rebuilt_digest_matches_release_pairs": sum(
                row["rebuilt_matches_release_digest"] for row in completed
            ),
            "repeated_build_digest_match_pairs": sum(
                row["repeated_build_digest_match"] for row in repeated_rows
            ),
            "repeated_build_pairs": len(repeated_rows),
            "migration_evaluations": sum(
                row["migration_evaluations"] for row in completed
            ),
            "migration_passed": sum(
                row["migration_passed"] for row in completed
            ),
        },
        "pairs": rows,
        "gate": {
            "name": "all offline rebuilds match release behavior contracts",
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
    parser.add_argument("--migration-trials", type=int, default=1)
    parser.add_argument("--build-repetitions", type=int, default=2)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.migration_trials < 1:
        parser.error("--migration-trials must be >= 1")
    if arguments.build_repetitions < 1:
        parser.error("--build-repetitions must be >= 1")
    report = run_benchmark(
        wheel_manifest_path=arguments.wheel_manifest,
        sdist_manifest_path=arguments.sdist_manifest,
        artifact_directory=arguments.artifact_directory,
        migration_trials=arguments.migration_trials,
        build_repetitions=arguments.build_repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "sdist-rebuild-parity",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
