"""Privacy-safe, scope-specific host aliases for local experiments."""

import hashlib
import hmac
import os
import stat
import tempfile
import uuid
from pathlib import Path
from typing import Dict


SCHEME = "sri-host-scope-hmac-sha256-v1"


def _read_secret(identity_path: Path) -> uuid.UUID:
    metadata = identity_path.lstat()
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError("host identity must be a regular file")
    if metadata.st_mode & 0o077:
        raise PermissionError("host identity permissions must exclude group/world")
    raw = identity_path.read_text(encoding="ascii").strip()
    try:
        value = uuid.UUID(raw)
    except (ValueError, AttributeError) as exc:
        raise ValueError("host identity is not a UUID") from exc
    if value.version != 4:
        raise ValueError("host identity must be UUIDv4")
    return value


def ensure_local_secret(identity_path: Path) -> uuid.UUID:
    """Create an atomic local UUIDv4 secret or validate the existing one."""
    identity_path = Path(os.path.abspath(identity_path))
    identity_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not identity_path.exists():
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=".sri-host-identity.",
            dir=identity_path.parent,
        )
        temporary = Path(temporary_name)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="ascii") as handle:
                handle.write(f"{uuid.uuid4()}\n")
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, identity_path)
            except FileExistsError:
                pass
        finally:
            temporary.unlink(missing_ok=True)
    return _read_secret(identity_path)


def scoped_host_alias(identity_path: Path, scope: str) -> Dict[str, str]:
    """Derive an exportable alias that is unlinkable across declared scopes."""
    if not scope or len(scope.encode("utf-8")) > 256:
        raise ValueError("scope must be 1-256 UTF-8 bytes")
    secret = ensure_local_secret(identity_path)
    digest = hmac.new(
        secret.bytes,
        scope.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return {
        "scheme": SCHEME,
        "scope": scope,
        "host_alias": f"sri_host_{digest[:32]}",
    }
