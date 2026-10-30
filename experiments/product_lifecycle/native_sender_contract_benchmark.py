#!/usr/bin/env python3
"""Audit published native sender identity, structure, and protocol behavior."""

import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, List, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


DEFAULT_MANIFEST = EXPERIMENT_DIR / "native_sender_manifest_v0.1.6.json"
REQUIRED_SYMBOLS = {"main"}
DIAGNOSTIC_SYMBOLS = {"argument_value", "write_all"}

LINUX_PROTOCOL_RUNNER = r"""
import json
import socket
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

binary = Path(sys.argv[1])
repetitions = int(sys.argv[2])

def run_contract():
    with tempfile.TemporaryDirectory(prefix="sri-linux-native-contract-") as d:
        socket_path = Path(d) / "hook.sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen()
        server.settimeout(5)
        received = []
        def consume():
            for _ in range(repetitions):
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    break
                chunks = []
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                connection.close()
                received.append(b"".join(chunks))
        thread = threading.Thread(target=consume, daemon=True)
        thread.start()
        processes = []
        payloads = []
        for index in range(repetitions):
            payload = json.dumps(
                {"session_id": f"linux-{index}", "tool_name": "Skill"},
                separators=(",", ":"),
            ).encode()
            payloads.append(payload)
            process = subprocess.run(
                [
                    str(binary), "--agent", "codex", "--event", "PreToolUse",
                    "--socket", str(socket_path),
                ],
                input=payload,
                capture_output=True,
                timeout=10,
            )
            processes.append(process)
        thread.join(timeout=5)
        server.close()
        header = b'{"agent":"codex","event":"PreToolUse"}\n'
        deliveries = sum(
            item == header + payload
            for item, payload in zip(received, payloads)
        )
        silent_successes = sum(
            process.returncode == 0
            and not process.stdout
            and not process.stderr
            for process in processes
        )
        missing = subprocess.run(
            [
                str(binary), "--agent", "codex", "--event", "PreToolUse",
                "--socket", str(Path(d) / "missing.sock"),
            ],
            input=b"{}",
            capture_output=True,
            timeout=10,
        )
        invalid = subprocess.run(
            [str(binary)],
            input=b"{}",
            capture_output=True,
            timeout=10,
        )
    return {
        "repetitions": repetitions,
        "exact_deliveries": deliveries,
        "silent_successes": silent_successes,
        "missing_socket_exit": missing.returncode,
        "missing_socket_silent": not missing.stdout and not missing.stderr,
        "invalid_arguments_exit": invalid.returncode,
        "invalid_arguments_silent": not invalid.stdout and not invalid.stderr,
        "passed": (
            deliveries == repetitions
            and silent_successes == repetitions
            and missing.returncode == 1
            and not missing.stdout
            and not missing.stderr
            and invalid.returncode == 2
            and not invalid.stdout
            and not invalid.stderr
        ),
    }

print(json.dumps(run_contract()))
"""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_sections(output: str) -> List[Dict[str, str]]:
    sections = []
    pattern = re.compile(
        r"^\s*\d+\s+(\S*)\s+([0-9a-fA-F]+)\s+"
        r"[0-9a-fA-F]+\s*(.*)$"
    )
    for line in output.splitlines():
        match = pattern.match(line)
        if match:
            sections.append(
                {
                    "name": match.group(1),
                    "size_hex": match.group(2).lower(),
                    "type": match.group(3).strip(),
                }
            )
    return sections


def _parse_symbols(output: str) -> List[Dict[str, str]]:
    symbols = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 3 and len(fields[-2]) == 1:
            symbols.append({"type": fields[-2], "name": fields[-1]})
        elif len(fields) == 2 and len(fields[0]) == 1:
            symbols.append({"type": fields[0], "name": fields[1]})
    return sorted(symbols, key=lambda row: (row["name"], row["type"]))


def _fingerprint(value: Any) -> str:
    canonical = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _structure_for_binary(
    binary: Path,
    os_name: str,
    label_architecture: str,
    root: Path,
) -> List[Dict[str, Any]]:
    slices = []
    if os_name == "darwin":
        architectures = ("arm64", "x86_64")
        for architecture in architectures:
            thin = root / f"{binary.name}-{architecture}"
            subprocess.run(
                [
                    "/usr/bin/lipo",
                    str(binary),
                    "-thin",
                    architecture,
                    "-output",
                    str(thin),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            slices.append(
                _structure_for_slice(thin, architecture, "macho")
            )
    else:
        slices.append(
            _structure_for_slice(
                binary,
                label_architecture,
                "elf",
            )
        )
    return slices


def _structure_for_slice(
    binary: Path,
    architecture: str,
    object_format: str,
) -> Dict[str, Any]:
    sections = _parse_sections(
        subprocess.run(
            ["/usr/bin/objdump", "-h", str(binary)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )
    symbols = _parse_symbols(
        subprocess.run(
            ["/usr/bin/nm", str(binary)],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )
    symbol_names = {row["name"].lstrip("_") for row in symbols}
    return {
        "architecture": architecture,
        "object_format": object_format,
        "section_count": len(sections),
        "section_fingerprint": _fingerprint(sections),
        "symbol_count": len(symbols),
        "symbol_fingerprint": _fingerprint(symbols),
        "required_symbols": {
            symbol: symbol in symbol_names for symbol in sorted(REQUIRED_SYMBOLS)
        },
        "required_symbols_present": REQUIRED_SYMBOLS.issubset(symbol_names),
        "diagnostic_internal_symbols": {
            symbol: symbol in symbol_names
            for symbol in sorted(DIAGNOSTIC_SYMBOLS)
        },
    }


def _run_protocol_contract(
    binary: Path,
    repetitions: int,
    *,
    launch_timeout_seconds: float = 10,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-native-protocol-",
        # Production already shortens Hook socket paths into /tmp when the
        # configured state root is long. Keep the protocol fixture on that
        # same path class: Darwin's AF_UNIX behavior becomes unreliable well
        # before the sockaddr_un byte limit on some host configurations.
        dir="/tmp",
    ) as directory:
        root = Path(directory)
        socket_path = root / "hook.sock"
        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen()
        server.settimeout(5)
        received: List[bytes] = []

        def consume() -> None:
            for _ in range(repetitions):
                try:
                    connection, _ = server.accept()
                except socket.timeout:
                    break
                chunks = []
                while True:
                    chunk = connection.recv(65536)
                    if not chunk:
                        break
                    chunks.append(chunk)
                connection.close()
                received.append(b"".join(chunks))

        thread = threading.Thread(target=consume, daemon=True)
        thread.start()
        payloads = []
        processes = []
        for index in range(repetitions):
            payload = json.dumps(
                {
                    "session_id": f"darwin-{index}",
                    "tool_name": "Skill",
                },
                separators=(",", ":"),
            ).encode("utf-8")
            payloads.append(payload)
            processes.append(
                subprocess.run(
                    [
                        str(binary),
                        "--agent",
                        "codex",
                        "--event",
                        "PreToolUse",
                        "--socket",
                        str(socket_path),
                    ],
                    input=payload,
                    capture_output=True,
                    timeout=launch_timeout_seconds,
                )
            )
        thread.join(timeout=5)
        server.close()
        header = b'{"agent":"codex","event":"PreToolUse"}\n'
        deliveries = sum(
            item == header + payload
            for item, payload in zip(received, payloads)
        )
        silent_successes = sum(
            process.returncode == 0
            and not process.stdout
            and not process.stderr
            for process in processes
        )
        missing = subprocess.run(
            [
                str(binary),
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
                "--socket",
                str(root / "missing.sock"),
            ],
            input=b"{}",
            capture_output=True,
            timeout=launch_timeout_seconds,
        )
        invalid = subprocess.run(
            [str(binary)],
            input=b"{}",
            capture_output=True,
            timeout=launch_timeout_seconds,
        )
    passed = (
        deliveries == repetitions
        and silent_successes == repetitions
        and missing.returncode == 1
        and not missing.stdout
        and not missing.stderr
        and invalid.returncode == 2
        and not invalid.stdout
        and not invalid.stderr
    )
    return {
        "repetitions": repetitions,
        "exact_deliveries": deliveries,
        "silent_successes": silent_successes,
        "missing_socket_exit": missing.returncode,
        "missing_socket_silent": not missing.stdout and not missing.stderr,
        "invalid_arguments_exit": invalid.returncode,
        "invalid_arguments_silent": not invalid.stdout and not invalid.stderr,
        "passed": passed,
    }


def _run_linux_protocol_contract(
    binary: Path,
    repetitions: int,
    image_ref: str,
    shared_temp_parent: Path,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-linux-native-protocol-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        copied = root / binary.name
        shutil.copy2(binary, copied)
        copied.chmod(0o755)
        runner = root / "runner.py"
        runner.write_text(LINUX_PROTOCOL_RUNNER, encoding="utf-8")
        process = subprocess.run(
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
                "/work/runner.py",
                f"/work/{binary.name}",
                str(repetitions),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
    return json.loads(process.stdout)


def run_benchmark(
    manifest_path: Path,
    artifact_directory: Path,
    linux_image_ref: str,
    shared_temp_parent: Path,
    repetitions: int = 20,
) -> Dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows = []
    with tempfile.TemporaryDirectory(
        prefix="sri-native-structure-"
    ) as directory:
        root = Path(directory)
        for entry in manifest["assets"]:
            binary = artifact_directory / entry["name"]
            if not binary.is_file():
                rows.append(
                    {
                        "name": entry["name"],
                        "status": "not_run",
                        "reason": "artifact_missing",
                        "passed": False,
                    }
                )
                continue
            actual_digest = _sha256(binary)
            identity_passed = (
                actual_digest == entry["sha256"]
                and binary.stat().st_size == entry["bytes"]
            )
            structures = _structure_for_binary(
                binary,
                entry["os"],
                entry["label_architecture"],
                root,
            )
            structure_passed = all(
                item["required_symbols_present"] for item in structures
            )
            functional = {
                "status": "not_run",
                "reason": "architecture_not_executed",
            }
            if entry["os"] == "darwin" and entry["label_architecture"] == "arm64":
                executable = root / entry["name"]
                shutil.copy2(binary, executable)
                executable.chmod(0o755)
                functional = {
                    "status": "completed",
                    **_run_protocol_contract(executable, repetitions),
                }
            elif entry["os"] == "linux" and entry["label_architecture"] == "arm64":
                functional = {
                    "status": "completed",
                    **_run_linux_protocol_contract(
                        binary,
                        repetitions,
                        linux_image_ref,
                        shared_temp_parent,
                    ),
                }
            rows.append(
                {
                    "name": entry["name"],
                    "os": entry["os"],
                    "label_architecture": entry["label_architecture"],
                    "status": "completed",
                    "raw_sha256": actual_digest,
                    "identity_passed": identity_passed,
                    "structures": structures,
                    "structure_passed": structure_passed,
                    "functional": functional,
                    "passed": (
                        identity_passed
                        and structure_passed
                        and (
                            functional.get("passed", False)
                            if functional["status"] == "completed"
                            else True
                        )
                    ),
                }
            )

    completed = [row for row in rows if row["status"] == "completed"]
    functional = [
        row for row in completed if row["functional"]["status"] == "completed"
    ]
    not_run_functional = [
        row for row in completed if row["functional"]["status"] == "not_run"
    ]
    darwin_rows = [row for row in completed if row["os"] == "darwin"]
    report = {
        "schema_version": "sri.experiment.native-sender-contract.v1",
        "experiment": {
            "name": "published-native-sender-four-layer-contract",
            "evidence_grade": "Experimental",
            "raw_evidence_grade": "Observed",
            "structure_evidence_grade": "Derived",
            "functional_evidence_grade": "Experimental",
            "repetitions_per_executed_asset": repetitions,
            "limitations": [
                "Functional protocol tests use a synthetic Unix-socket server, not a real Agent.",
                "Darwin x86_64 and Linux x86_64 binaries are not executed.",
                "Section/symbol fingerprints describe published files but do not prove source equivalence.",
                "The Linux arm64 execution uses a Docker VM hosted on the same macOS machine.",
                "Static helper symbols are diagnostic only because compiler optimization may inline them.",
            ],
            "symbol_contract": {
                "required_entry_points": sorted(REQUIRED_SYMBOLS),
                "diagnostic_internal_symbols": sorted(DIAGNOSTIC_SYMBOLS),
            },
        },
        "environment": {
            "host_system": platform.system(),
            "host_machine": platform.machine(),
            "linux_image_ref": linux_image_ref,
        },
        "metrics": {
            "manifest_assets": len(rows),
            "completed_assets": len(completed),
            "passed_assets": sum(row["passed"] for row in completed),
            "identity_passed_assets": sum(
                row["identity_passed"] for row in completed
            ),
            "structure_passed_assets": sum(
                row["structure_passed"] for row in completed
            ),
            "structure_slices": sum(
                len(row["structures"]) for row in completed
            ),
            "functional_completed_assets": len(functional),
            "functional_not_run_assets": len(not_run_functional),
            "functional_passed_assets": sum(
                row["functional"]["passed"] for row in functional
            ),
            "functional_exact_deliveries": sum(
                row["functional"]["exact_deliveries"] for row in functional
            ),
            "darwin_assets_byte_identical": (
                len(darwin_rows) == 2
                and len({row["raw_sha256"] for row in darwin_rows}) == 1
            ),
        },
        "assets": rows,
        "gate": {
            "name": "published native identity, structure, and supported protocol contracts",
            "passed": (
                len(completed) == len(rows)
                and all(row["passed"] for row in completed)
                and len(functional) == 2
                and all(row["functional"]["passed"] for row in functional)
            ),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--artifact-directory", type=Path, required=True)
    parser.add_argument("--linux-image-ref", required=True)
    parser.add_argument("--shared-temp-parent", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(
        manifest_path=arguments.manifest,
        artifact_directory=arguments.artifact_directory,
        linux_image_ref=arguments.linux_image_ref,
        shared_temp_parent=arguments.shared_temp_parent,
        repetitions=arguments.repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "native-sender-contract",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
