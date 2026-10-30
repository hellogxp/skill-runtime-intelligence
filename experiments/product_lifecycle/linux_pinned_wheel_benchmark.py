#!/usr/bin/env python3
"""Rebuild release sdists in a digest-pinned offline Linux container."""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


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
    _wheel_contract,
)
from experiments.product_lifecycle.sdist_rebuild_determinism_benchmark import (
    DEFAULT_SOURCE_DATE_EPOCH,
)
from experiments.product_lifecycle.wheel_normalized_content_benchmark import (
    _normalized_wheel_manifest,
    _timestamp_map,
)


CONTAINER_BUILDER = r"""
import json
import os
import platform
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

root = Path("/work")
configuration = json.loads((root / "config.json").read_text())
subprocess.run(
    [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--no-index",
        "--find-links",
        str(root / "deps"),
        *configuration["builder_requirements"],
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)
environment = dict(os.environ)
environment["SOURCE_DATE_EPOCH"] = configuration["source_date_epoch"]
for artifact in configuration["artifacts"]:
    sdist = root / "artifacts" / artifact["filename"]
    for repetition in range(configuration["build_repetitions"]):
        output = root / "out" / artifact["version"] / str(repetition)
        output.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-cache-dir",
                "--no-index",
                "--no-deps",
                "--no-build-isolation",
                "--wheel-dir",
                str(output),
                str(sdist),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            env=environment,
        )
builder = {
    "platform": platform.platform(),
    "python": platform.python_version(),
    "pip": version("pip"),
    "setuptools": version("setuptools"),
    "wheel": version("wheel"),
    "packaging": version("packaging"),
}
(root / "out" / "builder.json").write_text(json.dumps(builder))
subprocess.run(["chmod", "-R", "a+rwX", str(root / "out")], check=True)
"""


def _by_version(manifest: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["version"]: row for row in manifest["artifacts"]}


def _analyze_wheels(
    published: Path,
    rebuilt: Sequence[Path],
) -> Dict[str, Any]:
    published_normalized, published_rows = _normalized_wheel_manifest(
        published
    )
    rebuilt_normalized, rebuilt_rows = _normalized_wheel_manifest(rebuilt[0])
    rebuilt_digests = [_sha256(path) for path in rebuilt]
    published_timestamps = _timestamp_map(published)
    rebuilt_timestamps = _timestamp_map(rebuilt[0])
    timestamp_differences = sum(
        published_timestamps.get(name) != rebuilt_timestamps.get(name)
        for name in set(published_timestamps) | set(rebuilt_timestamps)
    )
    normalized_match = published_normalized == rebuilt_normalized
    member_name_match = set(published_rows) == set(rebuilt_rows)
    repeated_digest_match = len(set(rebuilt_digests)) == 1
    contract_parity = (
        _wheel_contract(published) == _wheel_contract(rebuilt[0])
    )
    return {
        "published_sha256": _sha256(published),
        "rebuilt_sha256": rebuilt_digests[0],
        "raw_digest_match": rebuilt_digests[0] == _sha256(published),
        "normalized_content_fingerprint": published_normalized,
        "normalized_content_match": normalized_match,
        "member_name_match": member_name_match,
        "repeated_digest_match": repeated_digest_match,
        "contract_parity": contract_parity,
        "timestamp_differences": timestamp_differences,
        "passed": (
            normalized_match
            and member_name_match
            and repeated_digest_match
            and contract_parity
        ),
    }


def run_benchmark(
    wheel_manifest_path: Path,
    sdist_manifest_path: Path,
    artifact_directory: Path,
    dependency_directory: Path,
    shared_temp_parent: Path,
    image_ref: str,
    builder_requirements: Sequence[str],
    build_repetitions: int = 2,
    source_date_epoch: str = DEFAULT_SOURCE_DATE_EPOCH,
    comparison_report_path: Optional[Path] = None,
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
    image = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", image_ref],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )[0]

    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-linux-pinned-builder-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        artifacts = root / "artifacts"
        dependencies = root / "deps"
        output = root / "out"
        artifacts.mkdir()
        dependencies.mkdir()
        output.mkdir()
        for dependency in dependency_directory.glob("*.whl"):
            shutil.copy2(dependency, dependencies / dependency.name)
        sdist_entries = []
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
            shutil.copy2(sdist, artifacts / sdist.name)
            sdist_entries.append(
                {"version": version, "filename": sdist.name}
            )
        configuration = {
            "artifacts": sdist_entries,
            "builder_requirements": list(builder_requirements),
            "build_repetitions": build_repetitions,
            "source_date_epoch": source_date_epoch,
        }
        (root / "config.json").write_text(
            json.dumps(configuration),
            encoding="utf-8",
        )
        (root / "container_builder.py").write_text(
            CONTAINER_BUILDER,
            encoding="utf-8",
        )
        subprocess.run(
            [
                "docker",
                "run",
                "--rm",
                "--network",
                "none",
                "-v",
                f"{root.resolve()}:/work",
                image_ref,
                "python",
                "/work/container_builder.py",
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=600,
        )
        builder = json.loads(
            (output / "builder.json").read_text(encoding="utf-8")
        )
        completed_versions = {row["version"] for row in rows}
        for version in versions:
            if version in completed_versions:
                continue
            wheel_entry = wheels[version]
            rebuilt = []
            for repetition in range(build_repetitions):
                candidates = list((output / version / str(repetition)).glob(
                    "*.whl"
                ))
                if len(candidates) != 1:
                    raise ValueError(
                        "Linux build did not produce exactly one wheel"
                    )
                rebuilt.append(candidates[0])
            analysis = _analyze_wheels(
                artifact_directory / wheel_entry["filename"],
                rebuilt,
            )
            rows.append(
                {
                    "version": version,
                    "status": "completed",
                    **analysis,
                }
            )

    rows.sort(key=lambda row: row["version"])
    comparison = None
    if comparison_report_path is not None:
        comparison_report = json.loads(
            comparison_report_path.read_text(encoding="utf-8")
        )
        comparison_rows = {
            row["version"]: row for row in comparison_report["pairs"]
        }
        for row in rows:
            if row["status"] != "completed":
                continue
            reference = comparison_rows.get(row["version"])
            row["comparison_rebuilt_sha256"] = (
                reference.get("rebuilt_sha256") if reference else None
            )
            row["cross_environment_raw_digest_match"] = (
                reference is not None
                and row["rebuilt_sha256"] == reference.get("rebuilt_sha256")
            )
        comparison = {
            "schema_version": comparison_report.get("schema_version"),
            "created_at": comparison_report.get("created_at"),
            "builder": comparison_report.get("builder"),
        }
    completed = [row for row in rows if row["status"] == "completed"]
    not_run = [row for row in rows if row["status"] == "not_run"]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.linux-pinned-wheel.v1",
        "experiment": {
            "name": "digest-pinned-linux-normalized-wheel-content",
            "evidence_grade": "Experimental",
            "source_date_epoch": source_date_epoch,
            "build_repetitions": build_repetitions,
            "container_network": "none",
            "limitations": [
                "Docker runs a Linux arm64 VM hosted by one macOS machine.",
                "Only pure-Python wheels and one container image are covered.",
                "Dependency wheels are content-addressed locally but not checked against repository attestations.",
                "Normalized equivalence is diagnostic, not release authentication.",
            ],
        },
        "container": {
            "requested_image_ref": image_ref,
            "image_id": image["Id"],
            "repo_digests": image.get("RepoDigests", []),
            "architecture": image["Architecture"],
            "os": image["Os"],
            "builder": builder,
            "builder_requirements": list(builder_requirements),
            "dependency_artifacts": [
                {
                    "filename": path.name,
                    "sha256": _sha256(path),
                }
                for path in sorted(dependency_directory.glob("*.whl"))
            ],
        },
        "host": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "logical_cpu_count": os.cpu_count(),
            "load_average_1m": load[0],
            "load_average_5m": load[1],
            "load_average_15m": load[2],
        },
        "comparison_report": comparison,
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
            "repeated_digest_match_pairs": sum(
                row["repeated_digest_match"] for row in completed
            ),
            "contract_parity_pairs": sum(
                row["contract_parity"] for row in completed
            ),
            "total_timestamp_differences": sum(
                row["timestamp_differences"] for row in completed
            ),
            "cross_environment_raw_digest_match_pairs": (
                sum(
                    row.get("cross_environment_raw_digest_match", False)
                    for row in completed
                )
                if comparison is not None
                else None
            ),
        },
        "pairs": rows,
        "cross_environment_gate": {
            "name": "Linux rebuild digests match comparison environment",
            "applicable": comparison is not None,
            "passed": (
                all(
                    row.get("cross_environment_raw_digest_match", False)
                    for row in completed
                )
                if comparison is not None
                else None
            ),
        },
        "gate": {
            "name": "Linux normalized wheel content and contracts match",
            "passed": (
                len(completed) == len(rows)
                and all(row["passed"] for row in completed)
                and (
                    all(
                        row.get(
                            "cross_environment_raw_digest_match",
                            False,
                        )
                        for row in completed
                    )
                    if comparison is not None
                    else True
                )
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
    parser.add_argument("--dependency-directory", type=Path, required=True)
    parser.add_argument("--shared-temp-parent", type=Path, required=True)
    parser.add_argument("--image-ref", required=True)
    parser.add_argument(
        "--builder-requirement",
        action="append",
        dest="builder_requirements",
        required=True,
    )
    parser.add_argument("--build-repetitions", type=int, default=2)
    parser.add_argument(
        "--source-date-epoch",
        default=DEFAULT_SOURCE_DATE_EPOCH,
    )
    parser.add_argument("--comparison-report", type=Path)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(
        wheel_manifest_path=arguments.wheel_manifest,
        sdist_manifest_path=arguments.sdist_manifest,
        artifact_directory=arguments.artifact_directory,
        dependency_directory=arguments.dependency_directory,
        shared_temp_parent=arguments.shared_temp_parent,
        image_ref=arguments.image_ref,
        builder_requirements=arguments.builder_requirements,
        build_repetitions=arguments.build_repetitions,
        source_date_epoch=arguments.source_date_epoch,
        comparison_report_path=arguments.comparison_report,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "linux-pinned-wheel",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
