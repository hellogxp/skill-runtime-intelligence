#!/usr/bin/env python3
"""Measure native sender launch sensitivity to executable path reuse."""

import argparse
import json
import platform
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

from experiments.common import percentile, write_report
from experiments.product_lifecycle.native_sender_contract_benchmark import (
    _sha256,
    _structure_for_binary,
)
from experiments.product_lifecycle.native_sender_rebuild_parity_benchmark import (
    DEFAULT_REBUILD_MANIFEST,
    DEFAULT_RELEASE_MANIFEST,
    _build_darwin,
    load_verified_source,
)


CELLS: Tuple[Tuple[str, str], ...] = (
    ("published", "stable_path"),
    ("rebuilt", "stable_path"),
    ("published", "fresh_path_copy"),
    ("rebuilt", "fresh_path_copy"),
)


def balanced_order(block: int) -> List[Tuple[str, str]]:
    offset = block % len(CELLS)
    rotated = list(CELLS[offset:] + CELLS[:offset])
    return list(reversed(rotated)) if (block // len(CELLS)) % 2 else rotated


def _codesign_metadata(binary: Path) -> Dict[str, Any]:
    display = subprocess.run(
        ["/usr/bin/codesign", "-dvvv", str(binary)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    verify = subprocess.run(
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
    fields = {}
    for line in (display.stdout + "\n" + display.stderr).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            fields[key.strip()] = value.strip()
    xattrs = subprocess.run(
        ["/usr/bin/xattr", str(binary)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "display_exit": display.returncode,
        "signature": fields.get("Signature", "unknown"),
        "identifier": fields.get("Identifier", "unknown"),
        "team_identifier": fields.get("TeamIdentifier", "unknown"),
        "flags": fields.get("CodeDirectory v", "unknown"),
        "verify_exit": verify.returncode,
        "verify_message": (verify.stdout + verify.stderr).strip()[:500],
        "extended_attribute_names": sorted(xattrs.stdout.splitlines()),
    }


def _launch_missing_socket(binary: Path, socket_path: Path) -> Dict[str, Any]:
    started = time.perf_counter_ns()
    process = subprocess.run(
        [
            str(binary),
            "--agent",
            "codex",
            "--event",
            "PreToolUse",
            "--socket",
            str(socket_path),
        ],
        input=b"{}",
        capture_output=True,
        timeout=60,
    )
    wall_ms = (time.perf_counter_ns() - started) / 1e6
    passed = (
        process.returncode == 1
        and not process.stdout
        and not process.stderr
    )
    return {
        "wall_ms": wall_ms,
        "exit_code": process.returncode,
        "stdout_bytes": len(process.stdout),
        "stderr_bytes": len(process.stderr),
        "passed": passed,
    }


def summarize(values: Sequence[float]) -> Dict[str, float]:
    return {
        "count": len(values),
        "min_ms": min(values),
        "p50_ms": statistics.median(values),
        "p95_ms": percentile(values, 0.95),
        "max_ms": max(values),
    }


def run_benchmark(
    rebuild_manifest_path: Path,
    release_manifest_path: Path,
    artifact_directory: Path,
    shared_temp_parent: Path,
    repetitions: int = 12,
) -> Dict[str, Any]:
    rebuild_manifest, source, _, source_identity = load_verified_source(
        rebuild_manifest_path
    )
    release_manifest = json.loads(
        release_manifest_path.read_text(encoding="utf-8")
    )
    published_name = "skill-runtime-hook-native-darwin-arm64"
    published_entry = next(
        item
        for item in release_manifest["assets"]
        if item["name"] == published_name
    )
    published_source = artifact_directory / published_name
    published_identity = {
        "name": published_name,
        "sha256": _sha256(published_source),
        "bytes": published_source.stat().st_size,
        "passed": (
            _sha256(published_source) == published_entry["sha256"]
            and published_source.stat().st_size == published_entry["bytes"]
        ),
    }

    with tempfile.TemporaryDirectory(
        prefix="sri-native-path-launch-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        source_path = root / "hook_sender.c"
        source_path.write_bytes(source)
        rebuilt_source = root / "rebuilt-darwin-universal2"
        build = _build_darwin(
            source_path,
            rebuilt_source,
            rebuild_manifest["build_flags"],
            rebuild_manifest["darwin_architectures"],
        )
        artifact_sources = {
            "published": published_source,
            "rebuilt": rebuilt_source,
        }
        stable_root = root / "stable"
        fresh_root = root / "fresh"
        structure_root = root / "structure"
        stable_root.mkdir()
        fresh_root.mkdir()
        structure_root.mkdir()
        stable_paths = {}
        metadata = {}
        structures = {}
        artifact_digests = {}
        for artifact, source_binary in artifact_sources.items():
            stable = stable_root / artifact
            shutil.copy2(source_binary, stable)
            stable.chmod(0o700)
            stable_paths[artifact] = stable
            artifact_digests[artifact] = _sha256(source_binary)
            metadata[artifact] = _codesign_metadata(stable)
            artifact_structure_root = structure_root / artifact
            artifact_structure_root.mkdir()
            structures[artifact] = _structure_for_binary(
                stable,
                "darwin",
                "arm64",
                artifact_structure_root,
            )

        rows = []
        for block in range(repetitions):
            for position, (artifact, condition) in enumerate(
                balanced_order(block)
            ):
                if condition == "stable_path":
                    executable = stable_paths[artifact]
                else:
                    executable = (
                        fresh_root / f"{artifact}-{block:03d}-{position}"
                    )
                    shutil.copy2(artifact_sources[artifact], executable)
                    executable.chmod(0o700)
                missing_socket = (
                    Path(tempfile.gettempdir())
                    / f"sri-path-launch-{block}-{position}.sock"
                )
                result = _launch_missing_socket(executable, missing_socket)
                rows.append(
                    {
                        "block": block,
                        "position": position,
                        "artifact": artifact,
                        "condition": condition,
                        "path_reused": condition == "stable_path",
                        **result,
                    }
                )

    summaries = {}
    for artifact, condition in CELLS:
        cell_rows = [
            row
            for row in rows
            if row["artifact"] == artifact
            and row["condition"] == condition
        ]
        summaries[f"{artifact}:{condition}"] = summarize(
            [row["wall_ms"] for row in cell_rows]
        )
    deltas = {}
    for artifact in ("published", "rebuilt"):
        stable_by_block = {
            row["block"]: row["wall_ms"]
            for row in rows
            if row["artifact"] == artifact
            and row["condition"] == "stable_path"
        }
        fresh_by_block = {
            row["block"]: row["wall_ms"]
            for row in rows
            if row["artifact"] == artifact
            and row["condition"] == "fresh_path_copy"
        }
        block_deltas = [
            fresh_by_block[block] - stable_by_block[block]
            for block in sorted(stable_by_block)
        ]
        deltas[artifact] = {
            "fresh_minus_stable_ms": summarize(block_deltas),
            "positive_blocks": sum(value > 0 for value in block_deltas),
        }

    correct_rows = sum(row["passed"] for row in rows)
    report = {
        "schema_version": "sri.experiment.native-path-launch.v1",
        "experiment": {
            "name": "native-sender-path-reuse-launch-sensitivity",
            "evidence_grade": "Experimental",
            "repetitions_per_cell": repetitions,
            "correctness_gate_only": True,
            "latency_gate": "descriptive_not_predeclared",
            "limitations": [
                "A fresh pathname is not a fresh OS cache, security scan, or machine.",
                "All trials share one macOS host and one scheduling interval.",
                "The missing-socket prewarm path is measured, not successful delivery.",
                "Code-sign metadata is observed but not experimentally manipulated.",
                "Latency differences are associations and do not identify a causal mechanism.",
            ],
        },
        "source_identity": source_identity,
        "published_identity": published_identity,
        "environment": {
            "host_system": platform.system(),
            "host_machine": platform.machine(),
            "compiler_version": build["compiler_version"],
            "trial_order": "four-cell rotation, reversed every four blocks",
        },
        "artifacts": {
            artifact: {
                "sha256": artifact_digests[artifact],
                "codesign": metadata[artifact],
                "structures": structures[artifact],
            }
            for artifact in artifact_digests
        },
        "metrics": {
            "total_trials": len(rows),
            "correct_trials": correct_rows,
            "silent_trials": sum(
                row["stdout_bytes"] == 0 and row["stderr_bytes"] == 0
                for row in rows
            ),
            "summaries": summaries,
            "paired_path_deltas": deltas,
        },
        "trials": rows,
        "gate": {
            "name": "path-reuse launch integrity",
            "passed": (
                source_identity["passed"]
                and published_identity["passed"]
                and all(
                    all(
                        slice_report["required_symbols_present"]
                        for slice_report in artifact_slices
                    )
                    for artifact_slices in structures.values()
                )
                and len(rows) == repetitions * len(CELLS)
                and correct_rows == len(rows)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--rebuild-manifest",
        type=Path,
        default=DEFAULT_REBUILD_MANIFEST,
    )
    parser.add_argument(
        "--release-manifest",
        type=Path,
        default=DEFAULT_RELEASE_MANIFEST,
    )
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--shared-temp-parent", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=12)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(
        rebuild_manifest_path=arguments.rebuild_manifest,
        release_manifest_path=arguments.release_manifest,
        artifact_directory=arguments.artifact_directory,
        shared_temp_parent=arguments.shared_temp_parent,
        repetitions=arguments.repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "native-path-launch",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
