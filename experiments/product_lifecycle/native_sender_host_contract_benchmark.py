#!/usr/bin/env python3
"""Run an identity-verified published native sender on the current host."""

import argparse
import json
import platform
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.product_lifecycle.native_sender_contract_benchmark import (
    _run_protocol_contract,
    _structure_for_binary,
)


DEFAULT_MANIFEST = EXPERIMENT_DIR / "native_sender_manifest_v0.1.6.json"


def _manifest_asset(manifest, name):
    matches = [asset for asset in manifest["assets"] if asset["name"] == name]
    if len(matches) != 1:
        raise ValueError(f"expected one manifest asset for {name!r}")
    return matches[0]


def run_benchmark(
    artifact: Path,
    manifest_path: Path,
    repetitions: int,
):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    asset = _manifest_asset(manifest, artifact.name)
    observed = {
        "bytes": artifact.stat().st_size,
        "sha256": sha256_path(artifact),
        "host_os": platform.system().lower(),
        "host_architecture": platform.machine().lower(),
    }
    identity_passed = (
        observed["bytes"] == asset["bytes"]
        and observed["sha256"] == asset["sha256"]
    )
    host_compatible = (
        observed["host_os"] == asset["os"]
        and observed["host_architecture"] == asset["label_architecture"]
    )
    structure = []
    protocol = {"status": "not_run", "passed": False}
    if identity_passed and host_compatible:
        structure = _structure_for_binary(
            artifact,
            asset["os"],
            asset["label_architecture"],
            artifact.parent,
        )
        protocol = {
            "status": "completed",
            **_run_protocol_contract(artifact, repetitions),
        }
    structure_passed = bool(structure) and all(
        item["required_symbols_present"] for item in structure
    )
    gate_passed = (
        identity_passed
        and host_compatible
        and structure_passed
        and protocol["passed"]
    )
    return {
        "schema_version": "sri.experiment.native-sender-host-contract.v1",
        "experiment": {
            "name": "published-native-sender-current-host-contract",
            "evidence_grade": "Experimental",
            "manifest_path": str(manifest_path.resolve()),
            "manifest_sha256": sha256_path(manifest_path),
            "release_tag": manifest["tag"],
            "limitations": [
                "One host execution does not establish cross-host reliability.",
                "Digest identity proves the release bytes, not hosted-builder reproducibility.",
                "Protocol checks cover exact local Unix-socket delivery and silent failure semantics only.",
            ],
        },
        "artifact": {
            "path": str(artifact.resolve()),
            "manifest": asset,
            "observed": observed,
            "identity_passed": identity_passed,
            "host_compatible": host_compatible,
        },
        "structure": structure,
        "protocol": protocol,
        "gate": {
            "name": "identity, host, structure, and protocol contract",
            "passed": gate_passed,
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repetitions < 1:
        parser.error("--repetitions must be positive")
    report = run_benchmark(
        arguments.artifact,
        arguments.manifest,
        arguments.repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "native-sender-host-contract",
        report,
        arguments.output,
    )
    print(json.dumps({"artifact": report["artifact"], "protocol": report["protocol"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
