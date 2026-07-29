"""Optional native sender for the latency-sensitive local hook fast path."""

import hashlib
import os
import platform
import shutil
import subprocess
import tempfile
import time
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from . import __version__
from .event_queue import default_state_root


RELEASE_BASE_URL = (
    "https://github.com/hellogxp/skill-runtime-intelligence/releases/download"
)
MAX_NATIVE_BYTES = 4 * 1024 * 1024


def native_hook_sender_path(state_root: Optional[Path] = None) -> Path:
    return (state_root or default_state_root()) / "bin" / "skill-runtime-hook-native"


def native_asset_name() -> str:
    system = platform.system().lower()
    machine = platform.machine().lower()
    os_name = {"darwin": "darwin", "linux": "linux"}.get(system, "")
    arch = {
        "x86_64": "x86_64",
        "amd64": "x86_64",
        "arm64": "arm64",
        "aarch64": "arm64",
    }.get(machine, "")
    if not os_name or not arch:
        return ""
    return f"skill-runtime-hook-native-{os_name}-{arch}"


def download_native_hook_sender(
    state_root: Optional[Path] = None,
    *,
    base_url: str = "",
    timeout_seconds: float = 8.0,
) -> Dict[str, Any]:
    """Install a checksum-verified release sender without requiring a compiler."""
    output = native_hook_sender_path(state_root)
    asset = native_asset_name()
    if not asset:
        return {
            "available": False,
            "downloaded": False,
            "path": str(output),
            "reason": "unsupported_platform",
        }
    release_root = (
        base_url
        or os.environ.get("SKILL_RUNTIME_RELEASE_BASE_URL")
        or f"{RELEASE_BASE_URL}/v{__version__}"
    ).rstrip("/")
    asset_url = f"{release_root}/{asset}"
    try:
        with urlopen(f"{asset_url}.sha256", timeout=timeout_seconds) as response:
            checksum_text = response.read(4096).decode("ascii", errors="strict")
        expected = checksum_text.strip().split()[0].lower()
        if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
            raise ValueError("invalid release checksum")
        with urlopen(asset_url, timeout=timeout_seconds) as response:
            payload = response.read(MAX_NATIVE_BYTES + 1)
        if not payload or len(payload) > MAX_NATIVE_BYTES:
            raise ValueError("native sender release asset is empty or too large")
        actual = hashlib.sha256(payload).hexdigest()
        if actual != expected:
            raise ValueError("native sender checksum mismatch")
        output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".skill-runtime-hook-native.", dir=str(output.parent)
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.chmod(0o700)
            os.replace(str(temporary), str(output))
        finally:
            temporary.unlink(missing_ok=True)
        return {
            "available": True,
            "downloaded": True,
            "path": str(output),
            "reason": "downloaded",
            "asset": asset,
            "sha256": actual,
        }
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeError, ValueError) as exc:
        return {
            "available": False,
            "downloaded": False,
            "path": str(output),
            "reason": "download_failed",
            "detail": str(exc)[:500],
            "asset": asset,
        }


def build_native_hook_sender(
    state_root: Optional[Path] = None,
    compiler: str = "",
) -> Dict[str, Any]:
    """Build a tiny AF_UNIX sender when a local C compiler is available."""
    output = native_hook_sender_path(state_root)
    if output.is_file() and os.access(output, os.X_OK):
        return {
            "available": True,
            "built": False,
            "path": str(output),
            "reason": "already_built",
        }
    selected_compiler = compiler or shutil.which("cc") or shutil.which("clang") or ""
    if not selected_compiler:
        return {
            "available": False,
            "built": False,
            "path": str(output),
            "reason": "compiler_unavailable",
        }
    source_resource = resources.files("skill_runtime_intelligence").joinpath(
        "native/hook_sender.c"
    )
    output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".skill-runtime-hook-native.",
        dir=str(output.parent),
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        # ``source_resource`` may live inside the standalone zipapp.  as_file()
        # materializes it for the compiler and also works for normal wheels.
        with resources.as_file(source_resource) as source_path:
            result = subprocess.run(
                [
                    selected_compiler,
                    "-O2",
                    "-std=c99",
                    str(source_path),
                    "-o",
                    str(temporary),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        if result.returncode != 0:
            return {
                "available": False,
                "built": False,
                "path": str(output),
                "reason": "compile_failed",
                "detail": result.stderr.decode("utf-8", errors="replace")[-500:],
            }
        temporary.chmod(0o700)
        os.replace(str(temporary), str(output))
        return {
            "available": True,
            "built": True,
            "path": str(output),
            "reason": "built",
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "available": False,
            "built": False,
            "path": str(output),
            "reason": "compile_failed",
            "detail": str(exc),
        }
    finally:
        if temporary.exists():
            temporary.unlink()


def prewarm_native_hook_sender(
    state_root: Optional[Path] = None,
    *,
    timeout_seconds: float = 10.0,
) -> Dict[str, Any]:
    """Pay one-time executable validation cost during install, without delivery."""
    output = native_hook_sender_path(state_root)
    if not output.is_file() or not os.access(output, os.X_OK):
        return {
            "attempted": False,
            "passed": False,
            "reason": "sender_unavailable",
        }
    try:
        prewarm_root = Path(
            tempfile.mkdtemp(prefix="skill-runtime-prewarm-", dir="/tmp")
        )
        prewarm_root.chmod(0o700)
    except OSError as exc:
        return {
            "attempted": False,
            "passed": False,
            "reason": "prewarm_path_unavailable",
            "detail": str(exc)[:500],
        }
    missing_socket = prewarm_root / "missing.sock"
    started = time.perf_counter_ns()
    try:
        process = subprocess.run(
            [
                str(output),
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
                "--socket",
                str(missing_socket),
            ],
            input=b"{}",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout_seconds,
        )
        passed = (
            process.returncode == 1
            and not process.stdout
            and not process.stderr
        )
        return {
            "attempted": True,
            "passed": passed,
            "reason": "expected_missing_socket" if passed else "unexpected_result",
            "wall_ms": (time.perf_counter_ns() - started) / 1e6,
            "exit_code": process.returncode,
            "stdout_bytes": len(process.stdout),
            "stderr_bytes": len(process.stderr),
        }
    except (OSError, subprocess.SubprocessError) as exc:
        return {
            "attempted": True,
            "passed": False,
            "reason": "prewarm_failed",
            "detail": str(exc)[:500],
            "wall_ms": (time.perf_counter_ns() - started) / 1e6,
        }
    finally:
        try:
            prewarm_root.rmdir()
        except OSError:
            pass


def install_native_hook_sender(
    state_root: Optional[Path] = None,
    compiler: str = "",
    *,
    download_first: bool = True,
) -> Dict[str, Any]:
    """Prefer a checksum-verified release asset, then fall back to a local build."""
    output = native_hook_sender_path(state_root)
    if output.is_file() and os.access(output, os.X_OK):
        result = {
            "available": True,
            "built": False,
            "downloaded": False,
            "path": str(output),
            "reason": "already_installed",
        }
        result["prewarm"] = prewarm_native_hook_sender(state_root)
        return result
    download = (
        download_native_hook_sender(state_root)
        if download_first
        else {"available": False, "reason": "download_skipped"}
    )
    if download.get("available"):
        download["prewarm"] = prewarm_native_hook_sender(state_root)
        return download
    built = build_native_hook_sender(state_root, compiler)
    if built.get("available"):
        built["download_fallback"] = download.get("reason")
        built["prewarm"] = prewarm_native_hook_sender(state_root)
        return built
    built["download"] = download
    return built
