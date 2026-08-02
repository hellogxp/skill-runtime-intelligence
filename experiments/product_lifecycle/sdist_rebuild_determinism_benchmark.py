#!/usr/bin/env python3
"""Measure fixed-epoch wheel rebuild repeatability and file-level drift."""

import argparse
import email
import hashlib
import json
import os
import platform
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
    _sha256,
)
from experiments.product_lifecycle.migration_sdist_rebuild_benchmark import (
    _build_wheel,
    _wheel_contract,
)


DEFAULT_SOURCE_DATE_EPOCH = "315532800"


def _by_version(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["version"]: row for row in manifest["artifacts"]}


def _wheel_file_manifest(path: Path) -> Dict[str, Dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: {
                "content_sha256": hashlib.sha256(
                    archive.read(name)
                ).hexdigest(),
                "date_time": list(archive.getinfo(name).date_time),
                "external_attr": archive.getinfo(name).external_attr,
                "compress_type": archive.getinfo(name).compress_type,
            }
            for name in archive.namelist()
        }


def _wheel_header(path: Path) -> Dict[str, str]:
    with zipfile.ZipFile(path) as archive:
        metadata_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/METADATA")
        )
        wheel_name = next(
            name
            for name in archive.namelist()
            if name.endswith(".dist-info/WHEEL")
        )
        metadata = email.message_from_bytes(archive.read(metadata_name))
        wheel = email.message_from_bytes(archive.read(wheel_name))
    return {
        "metadata_version": str(metadata["Metadata-Version"]),
        "wheel_generator": str(wheel.get("Generator", "")),
    }


def run_benchmark(
    wheel_manifest_path: Path,
    sdist_manifest_path: Path,
    artifact_directory: Path,
    build_repetitions: int = 3,
    source_date_epoch: str = DEFAULT_SOURCE_DATE_EPOCH,
) -> Dict[str, Any]:
    wheels = _by_version(
        json.loads(wheel_manifest_path.read_text(encoding="utf-8"))
    )
    sdists = _by_version(
        json.loads(sdist_manifest_path.read_text(encoding="utf-8"))
    )
    versions = sorted(set(wheels) | set(sdists))
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-fixed-epoch-rebuild-"
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
            if _sha256(release_wheel) != wheel_entry["sha256"]:
                raise ValueError("published wheel digest mismatch")
            if _sha256(sdist) != sdist_entry["sha256"]:
                raise ValueError("published sdist digest mismatch")
            rebuilt = [
                _build_wheel(
                    sdist,
                    root / version / f"build-{index}",
                    source_date_epoch=source_date_epoch,
                )
                for index in range(build_repetitions)
            ]
            rebuilt_digests = [_sha256(path) for path in rebuilt]
            repeated_digest_match = len(set(rebuilt_digests)) == 1
            release_files = _wheel_file_manifest(release_wheel)
            rebuilt_files = _wheel_file_manifest(rebuilt[0])
            common = set(release_files) & set(rebuilt_files)
            differing_content = sorted(
                name
                for name in common
                if release_files[name]["content_sha256"]
                != rebuilt_files[name]["content_sha256"]
            )
            differing_zip_metadata = sorted(
                name
                for name in common
                if {
                    key: release_files[name][key]
                    for key in ("date_time", "external_attr", "compress_type")
                }
                != {
                    key: rebuilt_files[name][key]
                    for key in ("date_time", "external_attr", "compress_type")
                }
            )
            contract_parity = (
                _wheel_contract(release_wheel)
                == _wheel_contract(rebuilt[0])
            )
            rows.append(
                {
                    "version": version,
                    "status": "completed",
                    "build_repetitions": build_repetitions,
                    "repeated_digest_match": repeated_digest_match,
                    "rebuilt_matches_published_digest": (
                        rebuilt_digests[0] == wheel_entry["sha256"]
                    ),
                    "contract_parity": contract_parity,
                    "published_header": _wheel_header(release_wheel),
                    "rebuilt_header": _wheel_header(rebuilt[0]),
                    "published_file_count": len(release_files),
                    "rebuilt_file_count": len(rebuilt_files),
                    "only_published_files": sorted(
                        set(release_files) - set(rebuilt_files)
                    ),
                    "only_rebuilt_files": sorted(
                        set(rebuilt_files) - set(release_files)
                    ),
                    "differing_common_content_files": differing_content,
                    "differing_common_zip_metadata_files": (
                        differing_zip_metadata
                    ),
                    "passed": repeated_digest_match and contract_parity,
                }
            )

    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.fixed-epoch-rebuild.v1",
        "experiment": {
            "name": "fixed-epoch-sdist-rebuild-repeatability",
            "evidence_grade": "Experimental",
            "source_date_epoch": source_date_epoch,
            "build_repetitions": build_repetitions,
            "build_network_disabled": True,
            "build_isolation_disabled": True,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "One local build toolchain and one fixed epoch are covered.",
                "There is no randomized control, so causal attribution is not supported.",
                "File-level drift is descriptive and excludes runtime behavior beyond the selected contract.",
                "Published build-environment details are inferred only from wheel metadata.",
            ],
        },
        "environment": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "python_version": platform.python_version(),
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
            "fixed_epoch_repeatable_pairs": sum(
                row["repeated_digest_match"] for row in completed
            ),
            "contract_parity_pairs": sum(
                row["contract_parity"] for row in completed
            ),
            "rebuilt_digest_matches_published_pairs": sum(
                row["rebuilt_matches_published_digest"] for row in completed
            ),
            "total_only_published_files": sum(
                len(row["only_published_files"]) for row in completed
            ),
            "total_only_rebuilt_files": sum(
                len(row["only_rebuilt_files"]) for row in completed
            ),
            "total_differing_common_content_files": sum(
                len(row["differing_common_content_files"])
                for row in completed
            ),
        },
        "pairs": rows,
        "gate": {
            "name": "fixed-epoch rebuilds repeat and preserve selected contracts",
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
    parser.add_argument("--build-repetitions", type=int, default=3)
    parser.add_argument(
        "--source-date-epoch",
        default=DEFAULT_SOURCE_DATE_EPOCH,
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.build_repetitions < 2:
        parser.error("--build-repetitions must be >= 2")
    report = run_benchmark(
        wheel_manifest_path=arguments.wheel_manifest,
        sdist_manifest_path=arguments.sdist_manifest,
        artifact_directory=arguments.artifact_directory,
        build_repetitions=arguments.build_repetitions,
        source_date_epoch=arguments.source_date_epoch,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "fixed-epoch-rebuild",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
