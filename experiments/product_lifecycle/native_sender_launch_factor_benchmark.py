#!/usr/bin/env python3
"""Run a balanced launch-factor experiment on temporary native copies."""

import argparse
import itertools
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.product_lifecycle.native_sender_contract_benchmark import (
    _sha256,
)
from experiments.product_lifecycle.native_sender_path_launch_benchmark import (
    _launch_missing_socket,
    summarize,
)


DEFAULT_FACTOR_MANIFEST = (
    EXPERIMENT_DIR / "native_sender_launch_factor_manifest_v2.json"
)
PLACEMENTS = ("direct_copy", "atomic_replace")
PROVENANCE_STATES = ("preserved", "removed")
SIGNATURE_STATES = ("original_linker", "adhoc_resigned")
CELLS: Tuple[Tuple[str, str, str], ...] = tuple(
    itertools.product(PLACEMENTS, PROVENANCE_STATES, SIGNATURE_STATES)
)


def balanced_order(
    block: int,
    cells: Sequence[Tuple[str, str, str]] = CELLS,
) -> List[Tuple[str, str, str]]:
    cells = tuple(cells)
    offset = block % len(cells)
    return list(cells[offset:] + cells[:offset])


def _xattr_names(binary: Path) -> List[str]:
    process = subprocess.run(
        ["/usr/bin/xattr", str(binary)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "xattr read failed")
    return sorted(process.stdout.splitlines())


def _strict_verify(binary: Path) -> Dict[str, Any]:
    process = subprocess.run(
        [
            "/usr/bin/codesign",
            "--verify",
            "--strict",
            "--verbose=4",
            str(binary),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "exit_code": process.returncode,
        "message": (process.stdout + process.stderr).strip()[:500],
    }


def _prepare_executable(
    source: Path,
    destination: Path,
    placement: str,
    provenance: str,
    signature: str,
) -> Dict[str, Any]:
    started = time.perf_counter_ns()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if placement == "direct_copy":
        shutil.copy2(source, destination)
    elif placement == "atomic_replace":
        staging = destination.with_suffix(".staging")
        shutil.copy2(source, staging)
        os.replace(staging, destination)
    else:
        raise ValueError(f"unsupported placement: {placement}")
    destination.chmod(0o700)

    resign = None
    if signature == "adhoc_resigned":
        process = subprocess.run(
            [
                "/usr/bin/codesign",
                "--force",
                "--sign",
                "-",
                "--timestamp=none",
                str(destination),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        resign = {
            "exit_code": process.returncode,
            "stdout": process.stdout.strip()[:500],
            "stderr": process.stderr.strip()[:500],
        }
    elif signature != "original_linker":
        raise ValueError(f"unsupported signature state: {signature}")

    if provenance == "removed":
        process = subprocess.run(
            [
                "/usr/bin/xattr",
                "-d",
                "com.apple.provenance",
                str(destination),
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        xattr_mutation = {
            "exit_code": process.returncode,
            "stderr": process.stderr.strip()[:500],
        }
    elif provenance == "preserved":
        xattr_mutation = {"exit_code": 0, "stderr": ""}
    else:
        raise ValueError(f"unsupported provenance state: {provenance}")

    xattrs_before_launch = _xattr_names(destination)
    verification = _strict_verify(destination)
    signature_applied = (
        resign is not None
        and resign["exit_code"] == 0
        and verification["exit_code"] == 0
        if signature == "adhoc_resigned"
        else verification["exit_code"] != 0
    )
    provenance_applied = (
        "com.apple.provenance" in xattrs_before_launch
        if provenance == "preserved"
        else (
            xattr_mutation["exit_code"] == 0
            and "com.apple.provenance" not in xattrs_before_launch
        )
    )
    return {
        "setup_wall_ms": (time.perf_counter_ns() - started) / 1e6,
        "sha256": _sha256(destination),
        "resign": resign,
        "xattr_mutation": xattr_mutation,
        "xattrs_before_launch": xattrs_before_launch,
        "strict_verification": verification,
        "signature_applied": signature_applied,
        "provenance_applied": provenance_applied,
        "placement_applied": True,
        "passed": (
            signature_applied
            and provenance_applied
            and xattr_mutation["exit_code"] == 0
        ),
    }


def factor_deltas(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    definitions = {
        "placement": ("direct_copy", "atomic_replace"),
        "provenance": ("preserved", "removed"),
        "signature": ("original_linker", "adhoc_resigned"),
    }
    by_block = sorted({row["block"] for row in rows})
    output = {}
    for factor, (baseline, alternate) in definitions.items():
        observed_levels = {row[factor] for row in rows}
        if not {baseline, alternate}.issubset(observed_levels):
            continue
        deltas = []
        for block in by_block:
            block_rows = [row for row in rows if row["block"] == block]
            baseline_values = [
                row["wall_ms"]
                for row in block_rows
                if row[factor] == baseline
            ]
            alternate_values = [
                row["wall_ms"]
                for row in block_rows
                if row[factor] == alternate
            ]
            deltas.append(
                statistics.fmean(alternate_values)
                - statistics.fmean(baseline_values)
            )
        output[factor] = {
            "contrast": f"{alternate}_minus_{baseline}",
            "delta_ms": summarize(deltas),
            "positive_blocks": sum(value > 0 for value in deltas),
        }
    return output


def run_benchmark(
    factor_manifest_path: Path,
    release_manifest_path: Path,
    artifact_directory: Path,
    shared_temp_parent: Path,
    repetitions: int,
) -> Dict[str, Any]:
    factor_manifest = json.loads(
        factor_manifest_path.read_text(encoding="utf-8")
    )
    release_manifest = json.loads(
        release_manifest_path.read_text(encoding="utf-8")
    )
    artifact_name = factor_manifest["artifact"]
    expected = next(
        item
        for item in release_manifest["assets"]
        if item["name"] == artifact_name
    )
    artifact = artifact_directory / artifact_name
    artifact_digest = _sha256(artifact)
    artifact_identity = {
        "name": artifact_name,
        "sha256": artifact_digest,
        "bytes": artifact.stat().st_size,
        "passed": (
            artifact_digest == expected["sha256"]
            and artifact.stat().st_size == expected["bytes"]
        ),
    }
    factor_cells = tuple(
        itertools.product(
            factor_manifest["factors"]["placement"],
            factor_manifest["factors"]["provenance"],
            factor_manifest["factors"]["signature"],
        )
    )
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-native-launch-factor-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        for block in range(repetitions):
            for position, (
                placement,
                provenance,
                signature,
            ) in enumerate(balanced_order(block, factor_cells)):
                executable = root / (
                    f"trial-{block:03d}-{position}-"
                    f"{placement}-{provenance}-{signature}"
                )
                setup = _prepare_executable(
                    artifact,
                    executable,
                    placement,
                    provenance,
                    signature,
                )
                missing_socket = (
                    Path(tempfile.gettempdir())
                    / f"sri-launch-factor-{block}-{position}.sock"
                )
                launch = _launch_missing_socket(executable, missing_socket)
                xattrs_after_launch = _xattr_names(executable)
                rows.append(
                    {
                        "block": block,
                        "position": position,
                        "placement": placement,
                        "provenance": provenance,
                        "signature": signature,
                        "factor_setup": setup,
                        "xattrs_after_launch": xattrs_after_launch,
                        **launch,
                    }
                )

    cell_summaries = {}
    for placement, provenance, signature in factor_cells:
        key = f"{placement}:{provenance}:{signature}"
        selected = [
            row["wall_ms"]
            for row in rows
            if row["placement"] == placement
            and row["provenance"] == provenance
            and row["signature"] == signature
        ]
        cell_summaries[key] = summarize(selected)
    correct = sum(row["passed"] for row in rows)
    setup_passed = sum(row["factor_setup"]["passed"] for row in rows)
    report = {
        "schema_version": "sri.experiment.native-launch-factor.v1",
        "experiment": {
            "name": factor_manifest["name"],
            "evidence_grade": "Experimental",
            "repetitions_per_cell": repetitions,
            "primary_endpoint": factor_manifest["primary_endpoint"],
            "latency_gate": factor_manifest["latency_gate"],
            "limitations": [
                "All cells run on one host and share system scheduling context.",
                "Temporary-path manipulation does not create a fresh machine or OS cache.",
                "Factor contrasts are descriptive until repeated across runs and hosts.",
                "Only the missing-socket prewarm contract is measured.",
            ],
        },
        "artifact_identity": artifact_identity,
        "factor_manifest": factor_manifest,
        "metrics": {
            "total_trials": len(rows),
            "correct_trials": correct,
            "factor_setup_passed_trials": setup_passed,
            "cell_summaries": cell_summaries,
            "factor_deltas": factor_deltas(rows),
            "provenance_reappeared_after_launch": sum(
                row["provenance"] == "removed"
                and "com.apple.provenance" in row["xattrs_after_launch"]
                for row in rows
            ),
        },
        "trials": rows,
        "gate": {
            "name": "temporary launch-factor integrity",
            "passed": (
                artifact_identity["passed"]
                and len(rows) == repetitions * len(factor_cells)
                and correct == len(rows)
                and setup_passed == len(rows)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--factor-manifest",
        type=Path,
        default=DEFAULT_FACTOR_MANIFEST,
    )
    parser.add_argument(
        "--release-manifest",
        type=Path,
        default=EXPERIMENT_DIR / "native_sender_manifest_v0.1.6.json",
    )
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--shared-temp-parent", type=Path, required=True)
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    factor_manifest = json.loads(
        arguments.factor_manifest.read_text(encoding="utf-8")
    )
    repetitions = (
        arguments.repetitions
        if arguments.repetitions is not None
        else factor_manifest["repetitions_per_cell"]
    )
    report = run_benchmark(
        factor_manifest_path=arguments.factor_manifest,
        release_manifest_path=arguments.release_manifest,
        artifact_directory=arguments.artifact_directory,
        shared_temp_parent=arguments.shared_temp_parent,
        repetitions=repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "native-launch-factor",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
