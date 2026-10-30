"""Versioned source adapters."""

from .codex import ADAPTER_VERSION as CODEX_ADAPTER_VERSION, CodexAdapter
from .observability import (
    ADAPTER_VERSION as OBSERVABILITY_ADAPTER_VERSION,
    ObservabilityAdapter,
    SUPPORTED_PROFILES,
)

__all__ = [
    "CODEX_ADAPTER_VERSION",
    "OBSERVABILITY_ADAPTER_VERSION",
    "CodexAdapter",
    "ObservabilityAdapter",
    "SUPPORTED_PROFILES",
]
