"""Privacy-safe pre-session correlation tokens for controlled experiments."""

import hashlib
import hmac
from pathlib import Path
from typing import Any, Dict

from experiments.privacy_safe_paired_task_key import ensure_study_secret


CORRELATION_SCHEMA = "sri.attempt-correlation.v1"
SCHEME = "sri-attempt-correlation-hmac-sha256-v1"
_DOMAIN = b"sri-attempt-correlation-v1\x00"


def _field(manifest: Dict[str, Any], name: str) -> str:
    value = manifest.get(name)
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


def attempt_correlation_token(
    secret_path: Path,
    manifest: Dict[str, Any],
) -> Dict[str, str]:
    """Derive an opaque token from an explicit attempt manifest."""
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be an object")
    if manifest.get("schema_version") != CORRELATION_SCHEMA:
        raise ValueError("unsupported attempt correlation schema")
    scope = _field(manifest, "study_scope")
    adapter = _field(manifest, "adapter")
    nonce = _field(manifest, "attempt_nonce")
    secret = ensure_study_secret(secret_path)
    message = b"".join([
        _DOMAIN,
        _length_prefixed(scope),
        _length_prefixed(adapter),
        _length_prefixed(nonce),
    ])
    digest = hmac.new(secret, message, hashlib.sha256).hexdigest()
    token = f"sri_corr_{digest[:32]}"
    return {
        "schema_version": CORRELATION_SCHEMA,
        "scheme": SCHEME,
        "study_scope": scope,
        "adapter": adapter,
        "token": token,
        "token_sha256": hashlib.sha256(token.encode("ascii")).hexdigest(),
    }
