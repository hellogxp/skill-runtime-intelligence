"""Security boundary for explicitly enabled self-hosted remote access."""

from __future__ import annotations

import base64
import ipaddress
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


MIN_TOKEN_CHARACTERS = 32


@dataclass(frozen=True)
class RemoteAccess:
    """In-memory remote access policy; token values are never persisted here."""

    enabled: bool = False
    viewer_token: str = ""
    ingest_token: str = ""
    tls_cert: Optional[Path] = None
    tls_key: Optional[Path] = None
    behind_https_proxy: bool = False

    @property
    def direct_tls(self) -> bool:
        return self.tls_cert is not None and self.tls_key is not None

    @property
    def transport(self) -> str:
        if not self.enabled:
            return "loopback"
        return "direct_tls" if self.direct_tls else "https_proxy"


def is_loopback_host(host: str) -> bool:
    candidate = host.strip().lower()
    if candidate == "localhost":
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def default_remote_secret_paths(state_root: Path) -> Dict[str, Path]:
    root = state_root.expanduser().resolve() / "secrets"
    return {
        "viewer": root / "remote-viewer.token",
        "ingest": root / "remote-ingest.token",
    }


def _write_new_secret(path: Path, value: str) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def initialize_remote_secrets(state_root: Path) -> Dict[str, object]:
    """Create independent viewer and ingest tokens without printing them."""
    paths = default_remote_secret_paths(state_root)
    created = []
    existing = []
    for role, path in paths.items():
        if path.exists():
            # Validate existing files rather than silently rotating credentials.
            read_secret_file(path)
            existing.append(role)
            continue
        _write_new_secret(path, secrets.token_urlsafe(32))
        created.append(role)
    return {
        "created": created,
        "existing": existing,
        "viewer_token_file": str(paths["viewer"]),
        "ingest_token_file": str(paths["ingest"]),
        "tokens_printed": False,
    }


def read_secret_file(path: Path) -> str:
    candidate = path.expanduser()
    if candidate.is_symlink():
        raise ValueError(f"refusing symlinked secret file: {candidate}")
    try:
        metadata = candidate.stat()
    except OSError as exc:
        raise ValueError(f"unable to read secret file {candidate}: {exc}") from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise ValueError(f"secret path is not a regular file: {candidate}")
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        raise ValueError(f"secret file must not be accessible by group/other: {candidate}")
    try:
        value = candidate.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"unable to read secret file {candidate}: {exc}") from exc
    if len(value) < MIN_TOKEN_CHARACTERS:
        raise ValueError(
            f"secret in {candidate} must contain at least {MIN_TOKEN_CHARACTERS} characters"
        )
    if any(character.isspace() for character in value):
        raise ValueError(f"secret in {candidate} must not contain whitespace")
    return value


def build_remote_access(
    *,
    enabled: bool,
    host: str,
    viewer_token_file: Optional[Path] = None,
    ingest_token_file: Optional[Path] = None,
    tls_cert: Optional[Path] = None,
    tls_key: Optional[Path] = None,
    behind_https_proxy: bool = False,
) -> RemoteAccess:
    if not enabled:
        if not is_loopback_host(host):
            raise ValueError(
                "non-loopback listening requires --remote and authenticated HTTPS"
            )
        if any((viewer_token_file, ingest_token_file, tls_cert, tls_key, behind_https_proxy)):
            raise ValueError("remote access options require --remote")
        return RemoteAccess()
    if viewer_token_file is None or ingest_token_file is None:
        raise ValueError(
            "remote mode requires separate --viewer-token-file and --ingest-token-file"
        )
    if viewer_token_file.expanduser().resolve() == ingest_token_file.expanduser().resolve():
        raise ValueError("viewer and ingest token files must be different")
    if (tls_cert is None) != (tls_key is None):
        raise ValueError("--tls-cert and --tls-key must be provided together")
    if tls_cert is None and not behind_https_proxy:
        raise ValueError(
            "remote mode requires direct TLS or --behind-https-proxy"
        )
    if tls_cert is not None and behind_https_proxy:
        raise ValueError("choose direct TLS or --behind-https-proxy, not both")
    if behind_https_proxy and not is_loopback_host(host):
        raise ValueError(
            "--behind-https-proxy must bind to loopback; expose only the HTTPS proxy"
        )
    cert = tls_cert.expanduser().resolve() if tls_cert else None
    key = tls_key.expanduser().resolve() if tls_key else None
    if cert and not cert.is_file():
        raise ValueError(f"TLS certificate not found: {cert}")
    if key and not key.is_file():
        raise ValueError(f"TLS key not found: {key}")
    if key and stat.S_IMODE(key.stat().st_mode) & 0o077:
        raise ValueError(f"TLS key must not be accessible by group/other: {key}")
    viewer_token = read_secret_file(viewer_token_file)
    ingest_token = read_secret_file(ingest_token_file)
    if secrets.compare_digest(viewer_token, ingest_token):
        raise ValueError("viewer and ingest tokens must be different")
    return RemoteAccess(
        enabled=True,
        viewer_token=viewer_token,
        ingest_token=ingest_token,
        tls_cert=cert,
        tls_key=key,
        behind_https_proxy=behind_https_proxy,
    )


def viewer_authorized(header: str, token: str) -> bool:
    if not header.startswith("Basic "):
        return False
    try:
        payload = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeError):
        return False
    username, separator, supplied = payload.partition(":")
    return bool(
        separator
        and username == "sri"
        and secrets.compare_digest(supplied, token)
    )


def ingest_authorized(header: str, token: str) -> bool:
    scheme, separator, supplied = header.partition(" ")
    return bool(
        separator
        and scheme.lower() == "bearer"
        and secrets.compare_digest(supplied.strip(), token)
    )
