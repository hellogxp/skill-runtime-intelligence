#!/usr/bin/env python3
"""Rebuild a verified native sender source and compare observable contracts."""

import argparse
import hashlib
import json
import platform
import shutil
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
    _run_linux_protocol_contract,
    _run_protocol_contract,
    _sha256,
    _structure_for_binary,
)


DEFAULT_REBUILD_MANIFEST = (
    EXPERIMENT_DIR / "native_sender_rebuild_manifest_v0.1.6.json"
)
DEFAULT_RELEASE_MANIFEST = (
    EXPERIMENT_DIR / "native_sender_manifest_v0.1.6.json"
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _git_bytes(tag: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{tag}:{path}"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def load_verified_source(
    manifest_path: Path,
) -> Tuple[Dict[str, Any], bytes, bytes, Dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    actual_commit = subprocess.run(
        ["git", "rev-parse", f"{manifest['tag']}^{{commit}}"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.strip()
    source = _git_bytes(manifest["tag"], manifest["source_path"])
    workflow = _git_bytes(manifest["tag"], manifest["workflow_path"])
    source_sha256 = _sha256_bytes(source)
    workflow_sha256 = _sha256_bytes(workflow)
    identity = {
        "tag_commit": actual_commit,
        "tag_commit_matches": actual_commit == manifest["commit"],
        "source_sha256": source_sha256,
        "source_matches": source_sha256 == manifest["source_sha256"],
        "workflow_sha256": workflow_sha256,
        "workflow_matches": workflow_sha256 == manifest["workflow_sha256"],
    }
    identity["passed"] = all(
        (
            identity["tag_commit_matches"],
            identity["source_matches"],
            identity["workflow_matches"],
        )
    )
    return manifest, source, workflow, identity


def _compiler_version(command: Sequence[str]) -> str:
    return subprocess.run(
        [*command, "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    ).stdout.splitlines()[0]


def _docker_image_identity(image_ref: str) -> Dict[str, Any]:
    value = json.loads(
        subprocess.run(
            ["docker", "image", "inspect", image_ref],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
    )[0]
    return {
        "requested_ref": image_ref,
        "digest_pinned": "@sha256:" in image_ref,
        "image_id": value["Id"],
        "architecture": value["Architecture"],
        "os": value["Os"],
        "repo_digests": value.get("RepoDigests", []),
    }


def _build_darwin(
    source: Path,
    output: Path,
    flags: Sequence[str],
    architectures: Sequence[str],
) -> Dict[str, Any]:
    compiler = shutil.which("cc") or shutil.which("clang")
    if not compiler:
        raise RuntimeError("Darwin compiler unavailable")
    command: List[str] = [compiler, *flags]
    for architecture in architectures:
        command.extend(("-arch", architecture))
    command.extend((str(source), "-o", str(output)))
    process = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    output.chmod(0o700)
    return {
        "command": command,
        "compiler_version": _compiler_version([compiler]),
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _build_linux(
    source: Path,
    output: Path,
    flags: Sequence[str],
    image_ref: str,
    shared_temp_parent: Path,
) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-native-linux-build-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        mounted_source = root / source.name
        shutil.copy2(source, mounted_source)
        mounted_output = root / output.name
        shell_command = (
            "cc "
            + " ".join(flags)
            + f" /work/{source.name} -o /work/{output.name}"
            + f" && chmod 700 /work/{output.name}"
            + " && cc --version | head -1"
        )
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "-v",
            f"{root.resolve()}:/work",
            image_ref,
            "bash",
            "-lc",
            shell_command,
        ]
        process = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=180,
        )
        shutil.copy2(mounted_output, output)
        output.chmod(0o700)
    return {
        "command": command,
        "compiler_version": process.stdout.strip().splitlines()[-1],
        "stdout": process.stdout,
        "stderr": process.stderr,
    }


def _structure_signature(structures: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "architecture": item["architecture"],
            "object_format": item["object_format"],
            "required_symbols_present": item["required_symbols_present"],
            "section_fingerprint": item["section_fingerprint"],
            "symbol_fingerprint": item["symbol_fingerprint"],
        }
        for item in structures
    ]


def _protocol_signature(result: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: result[key]
        for key in (
            "repetitions",
            "exact_deliveries",
            "silent_successes",
            "missing_socket_exit",
            "missing_socket_silent",
            "invalid_arguments_exit",
            "invalid_arguments_silent",
            "passed",
        )
    }


def _prewarm(binary: Path) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-native-rebuild-prewarm-"
    ) as directory:
        missing_socket = Path(directory) / "missing.sock"
        started = time.perf_counter_ns()
        process = subprocess.run(
            [
                str(binary),
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
                "--socket",
                str(missing_socket),
            ],
            input=b"{}",
            capture_output=True,
            timeout=60,
        )
    return {
        "wall_ms": (time.perf_counter_ns() - started) / 1e6,
        "exit_code": process.returncode,
        "stdout_bytes": len(process.stdout),
        "stderr_bytes": len(process.stderr),
        "passed": (
            process.returncode == 1
            and not process.stdout
            and not process.stderr
        ),
    }


def _compare_pair(
    *,
    os_name: str,
    architecture: str,
    published: Path,
    rebuilt: Path,
    structure_root: Path,
    repetitions: int,
    linux_runtime_image_ref: str,
    shared_temp_parent: Path,
) -> Dict[str, Any]:
    published_structures = _structure_for_binary(
        published,
        os_name,
        architecture,
        structure_root / f"{os_name}-published",
    )
    rebuilt_structures = _structure_for_binary(
        rebuilt,
        os_name,
        architecture,
        structure_root / f"{os_name}-rebuilt",
    )
    published_prewarm = None
    rebuilt_prewarm = None
    if os_name == "darwin":
        published_executable = structure_root / "darwin-published-executable"
        rebuilt_executable = structure_root / "darwin-rebuilt-executable"
        shutil.copy2(published, published_executable)
        shutil.copy2(rebuilt, rebuilt_executable)
        published_executable.chmod(0o700)
        rebuilt_executable.chmod(0o700)
        published_prewarm = _prewarm(published_executable)
        rebuilt_prewarm = _prewarm(rebuilt_executable)
        published_protocol = _run_protocol_contract(
            published_executable,
            repetitions,
        )
        rebuilt_protocol = _run_protocol_contract(
            rebuilt_executable,
            repetitions,
        )
    else:
        published_protocol = _run_linux_protocol_contract(
            published,
            repetitions,
            linux_runtime_image_ref,
            shared_temp_parent,
        )
        rebuilt_protocol = _run_linux_protocol_contract(
            rebuilt,
            repetitions,
            linux_runtime_image_ref,
            shared_temp_parent,
        )
    published_signature = _structure_signature(published_structures)
    rebuilt_signature = _structure_signature(rebuilt_structures)
    structure_contract_passed = (
        [
            (item["architecture"], item["object_format"])
            for item in published_signature
        ]
        == [
            (item["architecture"], item["object_format"])
            for item in rebuilt_signature
        ]
        and all(
            item["required_symbols_present"]
            for item in published_signature + rebuilt_signature
        )
    )
    protocol_parity = (
        _protocol_signature(published_protocol)
        == _protocol_signature(rebuilt_protocol)
    )
    published_sha256 = _sha256(published)
    rebuilt_sha256 = _sha256(rebuilt)
    return {
        "os": os_name,
        "architecture": architecture,
        "published_sha256": published_sha256,
        "rebuilt_sha256": rebuilt_sha256,
        "raw_digest_match": published_sha256 == rebuilt_sha256,
        "published_structures": published_structures,
        "rebuilt_structures": rebuilt_structures,
        "structure_contract_passed": structure_contract_passed,
        "section_fingerprint_parity": (
            [item["section_fingerprint"] for item in published_signature]
            == [item["section_fingerprint"] for item in rebuilt_signature]
        ),
        "symbol_fingerprint_parity": (
            [item["symbol_fingerprint"] for item in published_signature]
            == [item["symbol_fingerprint"] for item in rebuilt_signature]
        ),
        "published_protocol": published_protocol,
        "rebuilt_protocol": rebuilt_protocol,
        "published_prewarm": published_prewarm,
        "rebuilt_prewarm": rebuilt_prewarm,
        "protocol_parity": protocol_parity,
        "passed": (
            structure_contract_passed
            and (
                published_prewarm["passed"]
                and rebuilt_prewarm["passed"]
                if published_prewarm is not None
                else True
            )
            and published_protocol["passed"]
            and rebuilt_protocol["passed"]
            and protocol_parity
        ),
    }


def run_benchmark(
    rebuild_manifest_path: Path,
    release_manifest_path: Path,
    artifact_directory: Path,
    linux_build_image_ref: str,
    linux_runtime_image_ref: str,
    shared_temp_parent: Path,
    repetitions: int = 20,
) -> Dict[str, Any]:
    rebuild_manifest, source, _, source_identity = load_verified_source(
        rebuild_manifest_path
    )
    release_manifest = json.loads(
        release_manifest_path.read_text(encoding="utf-8")
    )
    release_assets = {
        item["name"]: item for item in release_manifest["assets"]
    }
    selected = {
        "darwin": "skill-runtime-hook-native-darwin-arm64",
        "linux": "skill-runtime-hook-native-linux-arm64",
    }
    published_identity = {}
    for os_name, name in selected.items():
        path = artifact_directory / name
        expected = release_assets[name]
        actual_sha256 = _sha256(path)
        published_identity[os_name] = {
            "name": name,
            "sha256": actual_sha256,
            "bytes": path.stat().st_size,
            "passed": (
                actual_sha256 == expected["sha256"]
                and path.stat().st_size == expected["bytes"]
            ),
        }

    with tempfile.TemporaryDirectory(
        prefix="sri-native-rebuild-",
        dir=shared_temp_parent,
    ) as directory:
        root = Path(directory)
        source_path = root / "hook_sender.c"
        source_path.write_bytes(source)
        darwin_output = root / "rebuilt-darwin-universal2"
        linux_output = root / "rebuilt-linux-arm64"
        darwin_build = _build_darwin(
            source_path,
            darwin_output,
            rebuild_manifest["build_flags"],
            rebuild_manifest["darwin_architectures"],
        )
        linux_build = _build_linux(
            source_path,
            linux_output,
            rebuild_manifest["build_flags"],
            linux_build_image_ref,
            shared_temp_parent,
        )
        structure_root = root / "structure"
        structure_root.mkdir()
        for name in (
            "darwin-published",
            "darwin-rebuilt",
            "linux-published",
            "linux-rebuilt",
        ):
            (structure_root / name).mkdir()
        pairs = [
            _compare_pair(
                os_name="darwin",
                architecture="arm64",
                published=artifact_directory / selected["darwin"],
                rebuilt=darwin_output,
                structure_root=structure_root,
                repetitions=repetitions,
                linux_runtime_image_ref=linux_runtime_image_ref,
                shared_temp_parent=shared_temp_parent,
            ),
            _compare_pair(
                os_name="linux",
                architecture="arm64",
                published=artifact_directory / selected["linux"],
                rebuilt=linux_output,
                structure_root=structure_root,
                repetitions=repetitions,
                linux_runtime_image_ref=linux_runtime_image_ref,
                shared_temp_parent=shared_temp_parent,
            ),
        ]

    build_identity = _docker_image_identity(linux_build_image_ref)
    runtime_identity = _docker_image_identity(linux_runtime_image_ref)
    report = {
        "schema_version": "sri.experiment.native-sender-rebuild-parity.v1",
        "experiment": {
            "name": "verified-source-native-sender-rebuild-parity",
            "evidence_grade": "Experimental",
            "source_evidence_grade": "Observed",
            "structure_evidence_grade": "Derived",
            "functional_evidence_grade": "Experimental",
            "repetitions_per_binary": repetitions,
            "limitations": [
                "The rebuilds use matching flags but not the original hosted runner images.",
                "Protocol tests use a synthetic Unix-socket server, not a real Agent.",
                "Linux build and runtime containers share the same macOS host.",
                "Only arm64 execution is covered; x86_64 remains not_run.",
                "Selected structure and protocol parity does not prove source equivalence or security.",
            ],
        },
        "source_identity": source_identity,
        "published_identity": published_identity,
        "environment": {
            "host_system": platform.system(),
            "host_machine": platform.machine(),
            "darwin_build": darwin_build,
            "linux_build": linux_build,
            "linux_build_image": build_identity,
            "linux_runtime_image": runtime_identity,
            "network_policy": "none for Linux build and runtime",
        },
        "metrics": {
            "source_identity_passed": source_identity["passed"],
            "published_identity_passed": sum(
                item["passed"] for item in published_identity.values()
            ),
            "completed_pairs": len(pairs),
            "passed_pairs": sum(item["passed"] for item in pairs),
            "raw_digest_matches": sum(
                item["raw_digest_match"] for item in pairs
            ),
            "section_fingerprint_matches": sum(
                item["section_fingerprint_parity"] for item in pairs
            ),
            "symbol_fingerprint_matches": sum(
                item["symbol_fingerprint_parity"] for item in pairs
            ),
            "functional_executions": len(pairs) * 2,
            "functional_exact_deliveries": sum(
                item["published_protocol"]["exact_deliveries"]
                + item["rebuilt_protocol"]["exact_deliveries"]
                for item in pairs
            ),
            "build_image_digest_pinned": build_identity["digest_pinned"],
            "runtime_image_digest_pinned": runtime_identity["digest_pinned"],
        },
        "pairs": pairs,
        "gate": {
            "name": "verified source to published native observable contract",
            "passed": (
                source_identity["passed"]
                and all(
                    item["passed"] for item in published_identity.values()
                )
                and build_identity["digest_pinned"]
                and runtime_identity["digest_pinned"]
                and len(pairs) == 2
                and all(item["passed"] for item in pairs)
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
    parser.add_argument("--linux-build-image-ref", required=True)
    parser.add_argument("--linux-runtime-image-ref", required=True)
    parser.add_argument("--shared-temp-parent", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=20)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(
        rebuild_manifest_path=arguments.rebuild_manifest,
        release_manifest_path=arguments.release_manifest,
        artifact_directory=arguments.artifact_directory,
        linux_build_image_ref=arguments.linux_build_image_ref,
        linux_runtime_image_ref=arguments.linux_runtime_image_ref,
        shared_temp_parent=arguments.shared_temp_parent,
        repetitions=arguments.repetitions,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "native-sender-rebuild-parity",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(json.dumps(report["gate"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
