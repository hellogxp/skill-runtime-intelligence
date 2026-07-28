"""Small, dependency-free redaction helpers used before persistence."""

import json
import re
from typing import Any


REDACTED = "[REDACTED]"
SENSITIVE_KEYS = re.compile(
    r"(authorization|api[_-]?key|access[_-]?token|refresh[_-]?token|password|passwd|secret|credential|private[_-]?key)",
    re.IGNORECASE,
)
SECRET_PATTERNS = (
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(
        r"(?i)\b(api[_-]?key|access[_-]?token|password|secret)\b"
        r"(\s*[=:]\s*)[\"']?[^\s,\"']{8,}"
    ),
)


def redact_text(value: str) -> str:
    result = value
    for pattern in SECRET_PATTERNS:
        if pattern.groups:
            result = pattern.sub(lambda match: f"{match.group(1)}{match.group(2)}{REDACTED}", result)
        else:
            result = pattern.sub(REDACTED, result)
    return result


def redact(value: Any, key: str = "") -> Any:
    if key and SENSITIVE_KEYS.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): redact(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redacted_json(value: Any) -> str:
    return json.dumps(redact(value), ensure_ascii=False, separators=(",", ":"))


def compact_text(value: Any, limit: int = 180) -> str:
    if value is None:
        return ""
    if not isinstance(value, str):
        value = json.dumps(redact(value), ensure_ascii=False, separators=(",", ":"))
    value = " ".join(redact_text(value).split())
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"
