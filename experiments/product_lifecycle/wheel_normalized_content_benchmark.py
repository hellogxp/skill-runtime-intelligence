#!/usr/bin/env python3
"""Compare published and pinned-builder wheels with normalized ZIP time."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Tuple


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
)
from experiments.product_lifecycle.migration_sdist_rebuild_benchmark import (
    _build_wheel,
    _wheel_contract,
)
from experiments.product_lifecycle.sdist_rebuild_determinism_benchmark import (
    DEFAULT_SOURCE_DATE_EPOCH,
)


def _by_version(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["version"]: row for row in manifest["artifacts"]}


def _normalized_wheel_manifest(
    path: Path,
) -> Tuple[str, Dict[str, Dict[str, Any]]]:
    with zipfile.ZipFile(path) as archive:
        rows = {
            name: {
                "content_sha256": hashlib.sha256(
                    archive.read(name)
                ).hexdigest(),
                "compress_type": archive.getinfo(name).compress_type,
                "external_attr": archive.getinfo(name).external_attr,
                "internal_attr": archive.getinfo(name).internal_attr,
                "create_system": archive.getinfo(name).create_system,
                "create_version": archive.getinfo(name).create_version,
                "extract_version": archive.getinfo(name).extract_version,
                "flag_bits": archive.getinfo(name).flag_bits,
            }
            for name in archive.namelist()
        }
    canonical = json.dumps(
        rows,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest(), rows


def _timestamp_map(path: Path) -> Dict[str, Tuple[int, ...]]:
    with zipfile.ZipFile(path) as archive:
        return {
            name: archive.getinfo(name).date_time
            for name in archive.namelist()
        }


def _builder_versions(python: Path) -> Dict[str, str]:
    probe = (
        "import json,platform\n"
        "from importlib.metadata import version\n"
        "print(json.dumps({'python': platform.python_version(),"
        "'pip': version('pip'), 'setuptools': version('setuptools'),"
        "'wheel': version('wheel')}))\n"
    )
    return json.loads(
        subprocess.run(
            [str(python), "-c", probe],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
            env=_isolated_subprocess_environment(),
            cwd=python.parent,
        ).stdout
    )


def run_benchmark(
    wheel_manifest_path: Path,
    sdist_manifest_path: Path,
    artifact_directory: Path,
    builder_python: Path,
    build_repetitions: int = 2,
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
        prefix="sri-normalized-wheel-content-"
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
            published = artifact_directory / wheel_entry["filename"]
            sdist = artifact_directory / sdist_entry["filename"]
            if not published.is_file() or not sdist.is_file():
                rows.append(
                    {
                        "version": version,
                        "status": "not_run",
                        "reason": "artifact_pair_missing",
                        "passed": False,
                    }
                )
                continue
            if _sha256(published) != wheel_entry["sha256"]:
                raise ValueError("published wheel digest mismatch")
            if _sha256(sdist) != sdist_entry["sha256"]:
                raise ValueError("published sdist digest mismatch")
            rebuilt = [
                _build_wheel(
                    sdist,
                    root / version / f"build-{index}",
                    source_date_epoch=source_date_epoch,
                    python_executable=builder_python,
                )
                for index in range(build_repetitions)
            ]
            rebuilt_digests = [_sha256(path) for path in rebuilt]
            published_normalized, published_rows = (
                _normalized_wheel_manifest(published)
            )
            rebuilt_normalized, rebuilt_rows = (
                _normalized_wheel_manifest(rebuilt[0])
            )
            normalized_match = published_normalized == rebuilt_normalized
            published_timestamps = _timestamp_map(published)
            rebuilt_timestamps = _timestamp_map(rebuilt[0])
            timestamp_differences = sum(
                published_timestamps.get(name)
                != rebuilt_timestamps.get(name)
                for name in set(published_timestamps) | set(rebuilt_timestamps)
            )
            raw_digest_match = (
                rebuilt_digests[0] == wheel_entry["sha256"]
            )
            repeated_digest_match = len(set(rebuilt_digests)) == 1
            contract_parity = (
                _wheel_contract(published) == _wheel_contract(rebuilt[0])
            )
            passed = (
                normalized_match
                and repeated_digest_match
                and contract_parity
                and set(published_rows) == set(rebuilt_rows)
            )
            rows.append(
                {
                    "version": version,
                    "status": "completed",
                    "published_sha256": wheel_entry["sha256"],
                    "rebuilt_sha256": rebuilt_digests[0],
                    "raw_digest_match": raw_digest_match,
                    "normalized_content_fingerprint": published_normalized,
                    "normalized_content_match": normalized_match,
                    "member_name_match": (
                        set(published_rows) == set(rebuilt_rows)
                    ),
                    "contract_parity": contract_parity,
                    "repeated_digest_match": repeated_digest_match,
                    "timestamp_differences": timestamp_differences,
                    "passed": passed,
                }
            )

    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.normalized-wheel-content.v1",
        "experiment": {
            "name": "pinned-builder-normalized-wheel-content",
            "evidence_grade": "Experimental",
            "source_date_epoch": source_date_epoch,
            "build_repetitions": build_repetitions,
            "normalized_fingerprint_excludes": ["ZIP member date_time"],
            "normalized_fingerprint_includes": [
                "member name",
                "decompressed content SHA-256",
                "compression type",
                "external/internal attributes",
                "creator/extractor versions",
                "flag bits",
            ],
            "limitations": [
                "The pinned builder runs on macOS, while published wheels were built on Ubuntu.",
                "One builder version and one epoch are covered.",
                "A normalized fingerprint is diagnostic and must not replace the release digest.",
                "Pure-Python wheel results do not generalize to native artifacts.",
            ],
        },
        "builder": _builder_versions(builder_python),
        "environment": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
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
            "raw_digest_match_pairs": sum(
                row["raw_digest_match"] for row in completed
            ),
            "normalized_content_match_pairs": sum(
                row["normalized_content_match"] for row in completed
            ),
            "member_name_match_pairs": sum(
                row["member_name_match"] for row in completed
            ),
            "contract_parity_pairs": sum(
                row["contract_parity"] for row in completed
            ),
            "repeated_digest_match_pairs": sum(
                row["repeated_digest_match"] for row in completed
            ),
            "total_timestamp_differences": sum(
                row["timestamp_differences"] for row in completed
            ),
        },
        "pairs": rows,
        "gate": {
            "name": "normalized wheel content and selected contracts match",
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
    parser.add_argument("--builder-python", type=Path, required=True)
    parser.add_argument("--build-repetitions", type=int, default=2)
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
        builder_python=arguments.builder_python,
        build_repetitions=arguments.build_repetitions,
        source_date_epoch=arguments.source_date_epoch,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "normalized-wheel-content",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
