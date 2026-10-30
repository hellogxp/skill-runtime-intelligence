#!/usr/bin/env python3
"""Exercise the packaged product lifecycle in a fully isolated local home."""

import argparse
import hashlib
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from skill_runtime_intelligence.runtime_manager import (
    _managed_process,
    _process_alive,
)


DEFAULT_CLEANUP_LEDGER = (
    EXPERIMENT_DIR / "results" / ".active-runtime-cleanup.json"
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command, environment, timeout=45):
    try:
        process = subprocess.run(
            [str(part) for part in command],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
    except OSError as exc:
        return {
            "return_code": 127,
            "stdout_json": None,
            "stdout_bytes": 0,
            "stderr_bytes": len(str(exc).encode("utf-8")),
            "stderr_tail": [str(exc)],
        }
    except subprocess.TimeoutExpired as exc:
        stderr = exc.stderr or ""
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return {
            "return_code": 124,
            "stdout_json": None,
            "stdout_bytes": len(exc.stdout or b""),
            "stderr_bytes": len(stderr.encode("utf-8")),
            "stderr_tail": stderr.splitlines()[-5:],
        }
    parsed = None
    try:
        parsed = json.loads(process.stdout)
    except (TypeError, ValueError, json.JSONDecodeError):
        pass
    return {
        "return_code": process.returncode,
        "stdout_json": parsed,
        "stdout_bytes": len(process.stdout.encode("utf-8")),
        "stderr_bytes": len(process.stderr.encode("utf-8")),
        "stderr_tail": process.stderr.splitlines()[-5:],
    }


def free_port():
    probe = socket.socket()
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    return port


def write_cleanup_ledger(source, destination):
    record = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise ValueError("runtime ownership record must be an object")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(record, separators=(",", ":"), sort_keys=True),
        encoding="utf-8",
    )
    temporary.chmod(0o600)
    temporary.replace(destination)


def recover_cleanup_ledger(path, wait_seconds=2.0):
    if not path.is_file():
        return {
            "ledger_found": False,
            "verified_process_found": False,
            "terminated": False,
        }
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        path.unlink(missing_ok=True)
        return {
            "ledger_found": True,
            "verified_process_found": False,
            "terminated": False,
        }
    verified = isinstance(record, dict) and _managed_process(record)
    terminated = False
    if verified:
        pid = int(record["pid"])
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + max(0.1, wait_seconds)
        while time.monotonic() < deadline and _process_alive(pid):
            time.sleep(0.05)
        if _process_alive(pid):
            os.kill(pid, signal.SIGKILL)
        terminated = True
    path.unlink(missing_ok=True)
    return {
        "ledger_found": True,
        "verified_process_found": verified,
        "terminated": terminated,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--wheel",
        type=Path,
        default=(
            REPOSITORY_ROOT
            / "dist"
            / "skill_runtime_intelligence-0.1.0-py3-none-any.whl"
        ),
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--cleanup-ledger",
        type=Path,
        default=DEFAULT_CLEANUP_LEDGER,
    )
    arguments = parser.parse_args()
    wheel = arguments.wheel.expanduser().resolve()
    if not wheel.is_file():
        parser.error(f"wheel does not exist: {wheel}")

    cleanup_recovery = recover_cleanup_ledger(arguments.cleanup_ledger)
    steps = {}
    cleanup_stop = None
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        home = root / "home"
        state = home / ".skill-runtime"
        project = root / "project"
        sessions = home / ".codex" / "sessions"
        environment_root = root / "venv"
        for path in (home, project, sessions):
            path.mkdir(parents=True)
        fixture = project / "do-not-modify.txt"
        fixture.write_text("packaged lifecycle fixture\n", encoding="utf-8")
        fixture_before = digest(fixture)

        environment = dict(os.environ)
        # Prevent an editable checkout or caller-provided source path from
        # satisfying imports and making a wheel smoke test pass spuriously.
        environment.pop("PYTHONPATH", None)
        environment.update(
            {
                "HOME": str(home),
                "SKILL_RUNTIME_HOME": str(state),
                "SKILL_RUNTIME_RELEASE_BASE_URL": "http://127.0.0.1:9",
                "PYTHONDONTWRITEBYTECODE": "1",
            }
        )
        steps["create_venv"] = run(
            [sys.executable, "-m", "venv", environment_root],
            environment,
        )
        python = environment_root / "bin" / "python"
        executable = environment_root / "bin" / "skill-runtime"
        steps["install_wheel"] = run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--no-index",
                "--no-deps",
                wheel,
            ],
            environment,
        )
        port = free_port()
        steps["install_product"] = run(
            [
                executable,
                "install",
                "--state-root",
                state,
                "--no-hooks",
                "--project",
                project,
                "--codex-sessions",
                sessions,
                "--executable",
                executable,
            ],
            environment,
        )
        start_command = [
            executable,
            "start",
            "--no-open",
            "--port",
            port,
            "--project",
            project,
            "--codex-sessions",
            sessions,
        ]
        stop_command = [
            executable,
            "stop",
            "--state-root",
            state,
            "--port",
            port,
        ]
        try:
            steps["start"] = run(start_command, environment)
            cleanup_stop = stop_command
            if steps["start"].get("return_code") == 0:
                write_cleanup_ledger(
                    state / "run" / "runtime.json",
                    arguments.cleanup_ledger,
                )
            steps["status_running"] = run(
                [
                    executable,
                    "status",
                    "--state-root",
                    state,
                    "--port",
                    port,
                ],
                environment,
            )
            steps["doctor"] = run(
                [
                    executable,
                    "doctor",
                    "--state-root",
                    state,
                    "--port",
                    port,
                ],
                environment,
            )
            steps["stop"] = run(stop_command, environment)
            cleanup_stop = None
            steps["status_stopped"] = run(
                [
                    executable,
                    "status",
                    "--state-root",
                    state,
                    "--port",
                    port,
                ],
                environment,
            )
            steps["uninstall"] = run(
                [
                    executable,
                    "uninstall",
                    "--state-root",
                    state,
                    "--yes",
                ],
                environment,
            )
        finally:
            if cleanup_stop is not None:
                run(cleanup_stop, environment)
            recover_cleanup_ledger(arguments.cleanup_ledger)

        project_unchanged = fixture.is_file() and digest(fixture) == fixture_before
        agent_configs_absent = not any(
            path.exists()
            for path in (
                home / ".codex" / "hooks.json",
                home / ".claude" / "settings.json",
            )
        )
        state_removed = not state.exists()

    install_result = steps["install_product"].get("stdout_json") or {}
    native_sender = install_result.get("native_hook_sender") or {}
    status_running = steps["status_running"].get("stdout_json") or {}
    doctor = steps["doctor"].get("stdout_json") or {}
    status_stopped = steps["status_stopped"].get("stdout_json") or {}
    expected_codes = {
        "create_venv": 0,
        "install_wheel": 0,
        "install_product": 0,
        "start": 0,
        "status_running": 0,
        "doctor": 1,
        "stop": 0,
        "status_stopped": 0,
        "uninstall": 0,
    }
    return_codes_match = all(
        steps[name]["return_code"] == expected
        for name, expected in expected_codes.items()
    )
    gate_passed = (
        return_codes_match
        and bool(install_result.get("installed"))
        and bool(native_sender.get("available"))
        and bool((native_sender.get("prewarm") or {}).get("passed"))
        and bool(status_running.get("running"))
        and not bool(doctor.get("ready_for_live_collection"))
        and not bool(status_stopped.get("running"))
        and project_unchanged
        and agent_configs_absent
        and state_removed
    )
    report = {
        "schema_version": "sri.experiment.product-lifecycle.v1",
        "experiment": {
            "name": "packaged-product-lifecycle",
            "evidence_grade": "Experimental",
            "wheel": wheel.name,
            "offline": True,
            "isolated_home": True,
            "live_agent_calls": False,
            "limitations": [
                "No live Agent hook was enabled or trusted.",
                "One local OS/Python environment is not cross-platform evidence.",
                "A lifecycle smoke test does not measure diagnosis usefulness.",
            ],
        },
        "metrics": {
            "expected_return_codes": expected_codes,
            "actual_return_codes": {
                name: value["return_code"] for name, value in steps.items()
            },
            "native_sender_available": bool(
                native_sender.get("available")
            ),
            "native_sender_reason": native_sender.get("reason"),
            "native_sender_prewarm_passed": bool(
                (native_sender.get("prewarm") or {}).get("passed")
            ),
            "native_sender_prewarm_wall_ms": (
                native_sender.get("prewarm") or {}
            ).get("wall_ms"),
            "running_after_start": bool(status_running.get("running")),
            "doctor_ready_for_live_collection": bool(
                doctor.get("ready_for_live_collection")
            ),
            "running_after_stop": bool(status_stopped.get("running")),
            "project_unchanged": project_unchanged,
            "agent_configs_absent": agent_configs_absent,
            "state_removed": state_removed,
            "prior_cleanup_recovery": cleanup_recovery,
            "step_diagnostics": steps,
        },
        "gate": {
            "name": "isolated offline packaged lifecycle",
            "passed": gate_passed,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "product-lifecycle", report, arguments.output
    )
    print(
        json.dumps(
            {
                "actual_return_codes": report["metrics"][
                    "actual_return_codes"
                ],
                "native_sender_available": report["metrics"][
                    "native_sender_available"
                ],
                "native_sender_reason": report["metrics"][
                    "native_sender_reason"
                ],
                "native_sender_prewarm_passed": report["metrics"][
                    "native_sender_prewarm_passed"
                ],
                "native_sender_prewarm_wall_ms": report["metrics"][
                    "native_sender_prewarm_wall_ms"
                ],
                "running_after_start": report["metrics"][
                    "running_after_start"
                ],
                "doctor_ready_for_live_collection": report["metrics"][
                    "doctor_ready_for_live_collection"
                ],
                "running_after_stop": report["metrics"][
                    "running_after_stop"
                ],
                "project_unchanged": project_unchanged,
                "agent_configs_absent": agent_configs_absent,
                "state_removed": state_removed,
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
