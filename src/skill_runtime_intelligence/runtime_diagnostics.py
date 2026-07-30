"""Truthful installation and live-collection diagnostics."""

import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, Optional

from .config import default_config_path, default_database_path, load_config
from .event_queue import default_event_queue, default_state_root
from .hook_bridge import default_hook_socket
from .integrations import (
    IntegrationError,
    inspect_claude_integration,
    inspect_codex_integration,
    inspect_opencode_integration,
    inspect_qoder_integration,
)
from .native_sender import native_hook_sender_path
from .runtime_manager import runtime_status
from .storage import Storage


def _writable_parent(path: Path) -> bool:
    parent = path if path.is_dir() else path.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    return parent.exists() and os.access(parent, os.W_OK)


def _socket_probe(path: Path) -> bool:
    if not path.is_socket():
        return False
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(0.2)
    try:
        client.connect(str(path))
        return True
    except OSError:
        return False
    finally:
        client.close()


def diagnose_runtime(
    *,
    state_root: Optional[Path] = None,
    config_path: Optional[Path] = None,
    database: Optional[Path] = None,
    host: str = "127.0.0.1",
    port: int = 4317,
) -> Dict[str, Any]:
    root = (state_root or default_state_root()).expanduser()
    config_file = (config_path or default_config_path(root)).expanduser()
    database_file = (database or default_database_path(root)).expanduser()
    queue = (
        root / "queue" / "events.jsonl"
        if state_root is not None
        else default_event_queue()
    )
    hook_socket = default_hook_socket(root)

    checks = []
    try:
        config = load_config(config_file)
        configured_database = Path(config["database"]).expanduser()
        checks.append(
            {
                "name": "config",
                "status": "pass",
                "detail": str(config_file),
            }
        )
        export = config.get("network_export", {})
        if isinstance(export, dict) and export.get("enabled"):
            checks.append(
                {
                    "name": "otlp_export",
                    "status": "pass" if export.get("endpoint") else "fail",
                    "detail": (
                        str(export.get("endpoint"))
                        if export.get("endpoint")
                        else "network export is enabled without an OTLP endpoint"
                    ),
                }
            )
        if database is None:
            database_file = configured_database
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        config = {}
        checks.append(
            {"name": "config", "status": "fail", "detail": str(exc)}
        )

    checks.append(
        {
            "name": "state_directory",
            "status": "pass" if _writable_parent(root) else "fail",
            "detail": str(root),
        }
    )
    runtime = runtime_status(root, host, port)
    if database is None and runtime.get("database"):
        database_file = Path(runtime["database"]).expanduser()
    checks.append(
        {
            "name": "collector",
            "status": "pass" if runtime["collector_healthy"] else "warn",
            "detail": (
                runtime["url"]
                if runtime["collector_healthy"]
                else "not running; use `skill-runtime start`"
            ),
        }
    )
    socket_live = _socket_probe(hook_socket)
    checks.append(
        {
            "name": "hook_transport",
            "status": "pass" if socket_live else "warn",
            "detail": str(hook_socket),
        }
    )
    checks.append(
        {
            "name": "offline_queue",
            "status": "pass" if _writable_parent(queue) else "fail",
            "detail": str(queue),
        }
    )

    sources = []
    if database_file.exists():
        try:
            storage = Storage(database_file)
            try:
                sources = storage.list_sources()
            finally:
                storage.close()
            checks.append(
                {
                    "name": "database",
                    "status": "pass",
                    "detail": str(database_file),
                }
            )
        except (OSError, ValueError) as exc:
            checks.append(
                {"name": "database", "status": "fail", "detail": str(exc)}
            )
    else:
        checks.append(
            {
                "name": "database",
                "status": "warn",
                "detail": f"not created: {database_file}",
            }
        )

    integrations = []
    for agent, inspector in (
        ("codex", inspect_codex_integration),
        ("claude-code", inspect_claude_integration),
        ("qoder", inspect_qoder_integration),
        ("opencode", inspect_opencode_integration),
    ):
        try:
            integration = inspector(state_root=root)
        except IntegrationError as exc:
            integration = {
                "agent": agent,
                "detected": True,
                "installed": False,
                "config_valid": False,
                "error": str(exc),
            }
        observed = [
            source
            for source in sources
            if source["adapter"] == agent
            and source["collection_mode"] == "official_hook"
        ]
        integration["live_evidence_seen"] = bool(observed)
        integration["live_evidence"] = observed
        if not integration.get("detected"):
            integration["connection_status"] = "not_detected"
        elif observed:
            integration["connection_status"] = "verified"
        elif integration.get("installed"):
            integration["connection_status"] = "awaiting_agent_trust_or_new_run"
        else:
            integration["connection_status"] = "not_configured"
        integrations.append(integration)

    detected = [item for item in integrations if item.get("detected")]
    configured = [item for item in detected if item.get("installed")]
    verified = [
        item for item in configured if item["connection_status"] == "verified"
    ]
    checks.append(
        {
            "name": "official_runtime_evidence",
            "status": "pass" if verified else ("warn" if configured else "fail"),
            "detail": (
                ", ".join(item["agent"] for item in verified)
                if verified
                else (
                    "hooks configured but no live official event observed; "
                    "restart the configured Agent and start a new turn; for "
                    "Codex, also review/trust the managed commands with `/hooks`"
                    if configured
                    else "no detected Agent has managed hooks configured"
                )
            ),
        }
    )
    native = native_hook_sender_path(root)
    checks.append(
        {
            "name": "native_sender",
            "status": "pass" if native.is_file() and os.access(native, os.X_OK) else "warn",
            "detail": (
                str(native)
                if native.exists()
                else "native fast path unavailable; Python fail-open fallback remains"
            ),
        }
    )
    return {
        "ok": not any(item["status"] == "fail" for item in checks),
        "ready_for_live_collection": bool(verified and runtime["collector_healthy"]),
        "checks": checks,
        "runtime": runtime,
        "integrations": integrations,
        "sources": sources,
    }
