"""Privacy-safe keys for explicit cross-Agent task assignments."""

import hashlib
import hmac
import os
import secrets
import stat
import tempfile
from pathlib import Path
from typing import Any, Dict


ASSIGNMENT_SCHEMA = "sri.paired-task-assignment.v1"
SCHEME = "sri-paired-task-hmac-sha256-v1"
_DOMAIN = b"sri-paired-task-key-v1\x00"
_SECRET_BYTES = 32


def _read_study_secret(secret_path: Path) -> bytes:
    metadata = secret_path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("study secret must be a regular file")
    if metadata.st_mode & 0o077:
        raise PermissionError(
            "study secret permissions must exclude group/world"
        )
    raw = secret_path.read_text(encoding="ascii").strip()
    try:
        secret = bytes.fromhex(raw)
    except ValueError as exc:
        raise ValueError("study secret must be hexadecimal") from exc
    if len(secret) != _SECRET_BYTES:
        raise ValueError("study secret must contain exactly 32 bytes")
    return secret


def ensure_study_secret(secret_path: Path) -> bytes:
    """Atomically create or validate a 256-bit study secret."""
    secret_path = Path(os.path.abspath(secret_path))
    secret_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not secret_path.exists():
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".sri-paired-task.",
            dir=secret_path.parent,
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                handle.write(f"{secrets.token_hex(_SECRET_BYTES)}\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, secret_path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    return _read_study_secret(secret_path)


def _field(assignment: Dict[str, Any], name: str) -> str:
    value = assignment.get(name)
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a string")
    encoded = value.encode("utf-8")
    if not encoded or len(encoded) > 256:
        raise ValueError(f"{name} must be 1-256 UTF-8 bytes")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{name} must not contain control characters")
    return value


def _length_prefixed(value: str) -> bytes:
    encoded = value.encode("utf-8")
    return len(encoded).to_bytes(2, "big") + encoded


def paired_task_key(
    secret_path: Path,
    assignment: Dict[str, Any],
) -> Dict[str, str]:
    """Derive an exportable key from an explicit study assignment."""
    if not isinstance(assignment, dict):
        raise ValueError("assignment must be an object")
    if assignment.get("schema_version") != ASSIGNMENT_SCHEMA:
        raise ValueError("unsupported paired-task assignment schema")
    study_scope = _field(assignment, "study_scope")
    protocol_version = _field(assignment, "protocol_version")
    task_id = _field(assignment, "task_id")
    secret = ensure_study_secret(secret_path)
    message = b"".join(
        [
            _DOMAIN,
            _length_prefixed(study_scope),
            _length_prefixed(protocol_version),
            _length_prefixed(task_id),
        ]
    )
    digest = hmac.new(secret, message, hashlib.sha256).hexdigest()
    return {
        "assignment_schema": ASSIGNMENT_SCHEMA,
        "scheme": SCHEME,
        "study_scope": study_scope,
        "protocol_version": protocol_version,
        "task_key": f"sri_task_{digest[:32]}",
    }
