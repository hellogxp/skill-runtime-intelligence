"""Command-line entry point."""

import argparse
import json
import os
import shutil
import sys
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import unquote
from urllib.parse import urlparse

from . import __version__
from .adapters import SUPPORTED_PROFILES
from .config import (
    default_config,
    default_config_path,
    default_database_path,
    load_config,
    normalized_paths,
    save_config,
)
from .discovery import default_skill_roots
from .event_queue import (
    DEFAULT_COLLECTOR_ENDPOINT,
    default_event_queue,
    deliver_or_queue,
    drain_remote_event_queue,
    watch_event_queue,
    watch_remote_event_queue,
)
from .hook_adapter import (
    HOOK_EVENT_TYPES,
    SUPPORTED_HOOK_AGENTS,
    build_hook_envelopes,
)
from .hook_bridge import default_hook_socket
from .indexer import import_observability, index_local, watch_local
from .integrations import (
    IntegrationError,
    enable_claude_hooks,
    enable_codex_hooks,
    enable_opencode_plugin,
    enable_qoder_hooks,
    inspect_claude_integration,
    inspect_codex_integration,
    inspect_opencode_integration,
    inspect_qoder_integration,
    remove_claude_hooks,
    remove_codex_hooks,
    remove_opencode_plugin,
    remove_qoder_hooks,
)
from .native_sender import build_native_hook_sender, install_native_hook_sender
from .otlp_exporter import export_otlp_once, watch_otlp_export
from .remote_access import (
    build_remote_access,
    default_remote_secret_paths,
    initialize_remote_secrets,
    is_loopback_host,
    read_secret_file,
)
from .runtime_diagnostics import diagnose_runtime
from .runtime_manager import (
    restart_runtime,
    runtime_status,
    start_runtime,
    stop_runtime,
)
from .server import serve
from .storage import Storage


MAX_HOOK_INPUT_BYTES = 1024 * 1024


def _path(value: str) -> Path:
    return Path(value).expanduser()


def _index_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--database", type=_path, default=default_database_path(),
        help="SQLite database path (default: ~/.skill-runtime/data/panorama.db)",
    )
    parser.add_argument(
        "--codex-sessions", type=_path, default=Path("~/.codex/sessions").expanduser(),
        help="Codex JSONL session root",
    )
    parser.add_argument(
        "--skill-root", action="append", type=_path, default=[],
        help="Additional Skill root; repeat for multiple roots",
    )
    parser.add_argument(
        "--project", type=_path, default=Path.cwd(),
        help="Project whose local Skill roots should be scanned",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        type=_path,
        default=[],
        help="Project or directory never read/indexed; repeat as needed",
    )
    parser.add_argument(
        "--config",
        type=_path,
        default=default_config_path(),
        help="Local Skill Runtime configuration path",
    )


def _roots(args) -> List[Path]:
    roots = default_skill_roots(args.project)
    try:
        config = load_config(getattr(args, "config", None))
    except (OSError, ValueError, json.JSONDecodeError):
        config = {}
    for project in config.get("projects", []):
        roots.extend(default_skill_roots(Path(project)))
    roots.extend(args.skill_root)
    return roots


def _run_index(args) -> dict:
    result = index_local(
        args.database,
        args.codex_sessions,
        _roots(args),
        _exclusions(args),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def _exclusions(args) -> List[Path]:
    values = list(getattr(args, "exclude", []) or [])
    config_path = getattr(args, "config", None)
    try:
        config = load_config(config_path)
    except (OSError, ValueError, json.JSONDecodeError):
        config = {}
    values.extend(Path(value) for value in config.get("exclude_paths", []))
    return [Path(value).expanduser() for value in normalized_paths(values)]


def _queue_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--event-queue",
        type=_path,
        default=default_event_queue(),
        help="Offline hook queue path",
    )
    parser.add_argument(
        "--hook-socket",
        type=_path,
        default=default_hook_socket(),
        help="Permission-restricted Unix socket for the low-latency Hook path",
    )


def _remote_server_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Enable authenticated self-hosted remote service mode",
    )
    parser.add_argument(
        "--viewer-token-file",
        type=_path,
        default=None,
        help="0600 token file used as the `sri` web/API Basic-auth password",
    )
    parser.add_argument(
        "--ingest-token-file",
        type=_path,
        default=None,
        help="Separate 0600 Bearer-token file accepted only by /api/events",
    )
    parser.add_argument(
        "--tls-cert",
        type=_path,
        default=None,
        help="PEM certificate for direct HTTPS",
    )
    parser.add_argument(
        "--tls-key",
        type=_path,
        default=None,
        help="PEM private key for direct HTTPS",
    )
    parser.add_argument(
        "--behind-https-proxy",
        action="store_true",
        help="Trust an HTTPS reverse proxy; requires a loopback backend bind",
    )


def _remote_access_from_args(args):
    viewer_file = getattr(args, "viewer_token_file", None)
    ingest_file = getattr(args, "ingest_token_file", None)
    if getattr(args, "remote", False) and (viewer_file is None or ingest_file is None):
        config_path = getattr(args, "config", default_config_path())
        defaults = default_remote_secret_paths(config_path.expanduser().resolve().parent)
        viewer_file = viewer_file or defaults["viewer"]
        ingest_file = ingest_file or defaults["ingest"]
    return build_remote_access(
        enabled=bool(getattr(args, "remote", False)),
        host=args.host,
        viewer_token_file=viewer_file,
        ingest_token_file=ingest_file,
        tls_cert=getattr(args, "tls_cert", None),
        tls_key=getattr(args, "tls_key", None),
        behind_https_proxy=bool(getattr(args, "behind_https_proxy", False)),
    )


def _server_scheme(args) -> str:
    return "https" if getattr(args, "tls_cert", None) else "http"


def _validated_relay_endpoint(endpoint: str) -> str:
    parsed = urlparse(endpoint)
    if parsed.scheme == "https" and parsed.netloc:
        return endpoint
    if (
        parsed.scheme == "http"
        and parsed.hostname
        and is_loopback_host(parsed.hostname)
    ):
        return endpoint
    raise ValueError("remote relay endpoint must use HTTPS (HTTP is loopback-only)")


def _start_queue_watcher(args) -> None:
    watcher = threading.Thread(
        target=watch_event_queue,
        args=(args.database, args.event_queue, 1.0),
        daemon=True,
        name="skill-runtime-event-queue",
    )
    watcher.start()


def _parse_headers(values: List[str]) -> dict:
    result = {}
    for value in values:
        key, separator, header_value = value.partition("=")
        if not separator or not key.strip():
            raise ValueError("OTLP headers must use NAME=VALUE")
        result[key.strip()] = header_value.strip()
    return result


def _environment_otlp_headers() -> Dict[str, str]:
    raw = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "")
    if not raw:
        return {}
    return _parse_headers(
        [unquote(item.strip()) for item in raw.split(",") if item.strip()]
    )


def _otlp_args(parser: argparse.ArgumentParser, endpoint_required: bool = False) -> None:
    default_endpoint = (
        os.environ.get("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")
        or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        or ""
    )
    parser.add_argument(
        "--otlp-endpoint",
        default=default_endpoint,
        required=endpoint_required and not default_endpoint,
        help="Opt-in OTLP/HTTP endpoint; /v1/traces is appended when omitted",
    )
    parser.add_argument(
        "--otlp-header",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="Runtime-only OTLP header; repeat for multiple headers",
    )
    parser.add_argument(
        "--otlp-batch-size",
        type=int,
        default=200,
        help="Maximum events per OTLP request",
    )
    parser.add_argument(
        "--otlp-interval",
        type=float,
        default=2.0,
        help="Seconds between OTLP export attempts",
    )


def _start_otlp_exporter(args) -> None:
    if not args.otlp_endpoint:
        return
    headers = _parse_headers(args.otlp_header) or _environment_otlp_headers()
    watcher = threading.Thread(
        target=watch_otlp_export,
        args=(
            args.database,
            args.otlp_endpoint,
            headers,
            args.otlp_interval,
            args.otlp_batch_size,
        ),
        daemon=True,
        name="skill-runtime-otlp-exporter",
    )
    watcher.start()


def _apply_runtime_config(args) -> None:
    """Resolve non-secret runtime defaults from the local config."""
    try:
        config = load_config(getattr(args, "config", None))
    except (OSError, ValueError, json.JSONDecodeError):
        return
    export = config.get("network_export", {})
    if (
        isinstance(export, dict)
        and export.get("enabled")
        and not getattr(args, "otlp_endpoint", "")
    ):
        args.otlp_endpoint = str(export.get("endpoint") or "")


def _start_retention_worker(args) -> None:
    """Apply configured retention now and periodically while the runtime is up."""
    try:
        config = load_config(getattr(args, "config", None))
        retention_days = config.get("retention_days")
        if retention_days is None:
            return
        retention_days = int(retention_days)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return

    def worker() -> None:
        while True:
            storage = Storage(args.database)
            try:
                result = storage.purge_expired(retention_days)
                if result["sessions_deleted"]:
                    print(
                        "Retention: removed "
                        f"{result['sessions_deleted']} expired indexed session(s); "
                        "Agent source files were not modified."
                    )
            finally:
                storage.close()
            threading.Event().wait(3600)

    watcher = threading.Thread(
        target=worker,
        daemon=True,
        name="skill-runtime-retention",
    )
    watcher.start()


def _browser_args(parser: argparse.ArgumentParser, default_open: bool) -> None:
    parser.set_defaults(open_browser=default_open)
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--open",
        dest="open_browser",
        action="store_true",
        help="Open the local Runtime UI after startup",
    )
    group.add_argument(
        "--no-open",
        dest="open_browser",
        action="store_false",
        help="Do not open a browser",
    )


def _schedule_browser(args) -> None:
    if not getattr(args, "open_browser", False):
        return
    host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    url = f"{_server_scheme(args)}://{host}:{args.port}/"
    timer = threading.Timer(0.7, lambda: webbrowser.open(url))
    timer.daemon = True
    timer.start()


def _open_runtime(args) -> None:
    if not getattr(args, "open_browser", False):
        return
    host = "127.0.0.1" if args.host in {"0.0.0.0", "::"} else args.host
    webbrowser.open(f"{_server_scheme(args)}://{host}:{args.port}/")


def _current_executable() -> str:
    candidate = Path(sys.argv[0]).expanduser()
    if candidate.exists() and (
        candidate.name in {"skill-runtime", "skill-panorama"}
        or candidate.suffix == ".pyz"
    ):
        return str(candidate.resolve())
    return shutil.which("skill-runtime") or ""


def _cli_invocation() -> List[str]:
    executable = _current_executable()
    if executable:
        return [executable]
    return [sys.executable, "-m", "skill_runtime_intelligence"]


def _run_hook(args) -> None:
    """Hook process boundary: intentionally silent and always fail-open."""
    try:
        raw = sys.stdin.buffer.read(MAX_HOOK_INPUT_BYTES + 1)
        if not raw or len(raw) > MAX_HOOK_INPUT_BYTES:
            return
        payload = json.loads(raw)
        envelopes = build_hook_envelopes(args.agent, args.event, payload)
        try:
            token = read_secret_file(args.token_file) if args.token_file else ""
        except ValueError:
            # Delivery will fail closed at a remote endpoint and preserve the
            # already-redacted event in the local durable queue.
            token = ""
        deliver_or_queue(
            envelopes,
            endpoint=args.endpoint,
            queue_path=args.event_queue,
            timeout_seconds=max(0.01, args.timeout_ms / 1000),
            token=token,
        )
    except Exception:
        return


def _run_live_runtime(args, *, index_first: bool = True) -> None:
    index_ready = threading.Event()
    if index_first:
        _run_index(args)
        index_ready.set()
    else:
        def index_worker() -> None:
            try:
                _run_index(args)
            finally:
                index_ready.set()

        initial_index = threading.Thread(
            target=index_worker,
            daemon=True,
            name="skill-runtime-initial-index",
        )
        initial_index.start()
    _start_queue_watcher(args)
    _start_otlp_exporter(args)
    _start_retention_worker(args)
    def watch_worker() -> None:
        index_ready.wait()
        watch_local(
            args.database,
            args.codex_sessions,
            _roots(args),
            args.watch_interval,
            _exclusions(args),
        )

    watcher = threading.Thread(
        target=watch_worker,
        daemon=True,
        name="skill-runtime-watch",
    )
    watcher.start()
    _schedule_browser(args)
    serve(
        args.database,
        args.host,
        args.port,
        event_queue=args.event_queue,
        hook_socket=args.hook_socket,
        config_path=args.config,
        remote_access=_remote_access_from_args(args),
    )


def _background_command(args) -> List[str]:
    command = _cli_invocation() + [
        "start",
        "--foreground",
        "--no-open",
        "--database",
        str(args.database.expanduser().resolve()),
        "--codex-sessions",
        str(args.codex_sessions.expanduser().resolve()),
        "--project",
        str(args.project.expanduser().resolve()),
        "--config",
        str(args.config.expanduser().resolve()),
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--watch-interval",
        str(args.watch_interval),
        "--event-queue",
        str(args.event_queue.expanduser().resolve()),
        "--hook-socket",
        str(args.hook_socket.expanduser().resolve()),
        "--otlp-batch-size",
        str(args.otlp_batch_size),
        "--otlp-interval",
        str(args.otlp_interval),
    ]
    if args.state_root:
        command.extend(["--state-root", str(args.state_root.expanduser().resolve())])
    if args.otlp_endpoint:
        command.extend(["--otlp-endpoint", args.otlp_endpoint])
    if getattr(args, "remote", False):
        command.append("--remote")
        for option, value in (
            ("--viewer-token-file", args.viewer_token_file),
            ("--ingest-token-file", args.ingest_token_file),
            ("--tls-cert", args.tls_cert),
            ("--tls-key", args.tls_key),
        ):
            if value:
                command.extend([option, str(value.expanduser().resolve())])
        if args.behind_https_proxy:
            command.append("--behind-https-proxy")
    for root in args.skill_root:
        command.extend(["--skill-root", str(root.expanduser().resolve())])
    for exclusion in args.exclude:
        command.extend(["--exclude", str(exclusion.expanduser().resolve())])
    return command


def _set_config_value(config: Dict[str, Any], assignment: str) -> None:
    key, separator, raw_value = assignment.partition("=")
    if not separator:
        raise ValueError("config values must use KEY=VALUE")
    key = key.strip()
    allowed = {
        "retention_days",
        "network_export.enabled",
        "network_export.endpoint",
    }
    if key not in allowed:
        raise ValueError(
            f"unsupported config key `{key}`; allowed: {', '.join(sorted(allowed))}"
        )
    value: Any = raw_value.strip()
    if key == "retention_days":
        if value.lower() in {"", "null", "none"}:
            value = None
        else:
            value = int(value)
            if value < 1 or value > 3650:
                raise ValueError("retention_days must be 1..3650 or null")
        config[key] = value
        return
    if key == "network_export.enabled":
        lowered = value.lower()
        if lowered not in {"true", "false"}:
            raise ValueError("network_export.enabled must be true or false")
        value = lowered == "true"
    config.setdefault("network_export", {})[key.rsplit(".", 1)[1]] = value


def _safe_remove_state_root(root: Path) -> None:
    resolved = root.expanduser().resolve()
    home = Path.home().resolve()
    if resolved in {Path("/"), home} or len(resolved.parts) < 3:
        raise ValueError(f"refusing to remove unsafe state path: {resolved}")
    config_path = resolved / "config.json"
    if config_path.exists():
        config = load_config(config_path)
        if not str(config.get("version", "")).startswith("skill-runtime-config-"):
            raise ValueError(f"refusing to remove unrecognized state directory: {resolved}")
    shutil.rmtree(resolved)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skill-runtime",
        description="Local-first, evidence-graded Agent Skill runtime panorama",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    install_parser = subparsers.add_parser(
        "install",
        help="Detect Agents, scan Skills, create the local index, and plan hooks",
    )
    install_parser.add_argument(
        "--state-root",
        type=_path,
        default=None,
        help=argparse.SUPPRESS,
    )
    install_parser.add_argument("--project", type=_path, default=Path.cwd())
    install_parser.add_argument(
        "--exclude", action="append", type=_path, default=[]
    )
    install_parser.add_argument(
        "--enable-hooks",
        action="store_true",
        help="Explicitly consent to fail-open hooks for detected Agents",
    )
    install_parser.add_argument(
        "--no-hooks",
        action="store_true",
        help="Record that hooks were declined; transcript remains fallback",
    )
    install_parser.add_argument(
        "--codex-sessions",
        type=_path,
        default=Path("~/.codex/sessions").expanduser(),
    )
    install_parser.add_argument("--executable", default="", help=argparse.SUPPRESS)

    index_parser = subparsers.add_parser("index", help="Index local Skills and Codex sessions")
    _index_args(index_parser)

    serve_parser = subparsers.add_parser("serve", help="Serve an existing local index")
    serve_parser.add_argument(
        "--database", type=_path, default=default_database_path()
    )
    serve_parser.add_argument(
        "--config", type=_path, default=default_config_path()
    )
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=4317)
    _remote_server_args(serve_parser)
    _queue_args(serve_parser)
    _otlp_args(serve_parser)
    _browser_args(serve_parser, False)

    dev_parser = subparsers.add_parser("dev", help="Index once, then open the local UI")
    _index_args(dev_parser)
    dev_parser.add_argument("--host", default="127.0.0.1")
    dev_parser.add_argument("--port", type=int, default=4317)
    dev_parser.add_argument(
        "--watch-interval",
        type=float,
        default=2.0,
        help="Seconds between incremental transcript checks (default: 2)",
    )
    _queue_args(dev_parser)
    _otlp_args(dev_parser)
    _browser_args(dev_parser, True)

    start_parser = subparsers.add_parser(
        "start", help="Start the local Collector, live index, and runtime UI"
    )
    start_parser.add_argument(
        "--state-root",
        type=_path,
        default=None,
        help=argparse.SUPPRESS,
    )
    _index_args(start_parser)
    start_parser.add_argument("--host", default="127.0.0.1")
    start_parser.add_argument("--port", type=int, default=4317)
    _remote_server_args(start_parser)
    start_parser.add_argument(
        "--watch-interval",
        type=float,
        default=2.0,
        help="Seconds between incremental transcript checks (default: 2)",
    )
    _queue_args(start_parser)
    _otlp_args(start_parser)
    _browser_args(start_parser, True)
    start_parser.add_argument(
        "--foreground",
        action="store_true",
        help="Run attached to this terminal instead of as a managed local process",
    )

    for command, help_text in (
        ("stop", "Stop the managed local Collector and UI"),
        ("restart", "Restart the managed local Collector and UI"),
        ("status", "Show managed process and Collector health"),
        ("doctor", "Verify installation, transport, hooks, and live evidence"),
    ):
        lifecycle = subparsers.add_parser(command, help=help_text)
        lifecycle.add_argument("--state-root", type=_path, default=None)
        lifecycle.add_argument("--host", default="127.0.0.1")
        lifecycle.add_argument("--port", type=int, default=4317)
        if command in {"restart"}:
            lifecycle.add_argument("--no-open", action="store_true")

    config_parser = subparsers.add_parser(
        "config", help="Show or update non-secret runtime configuration"
    )
    config_parser.add_argument(
        "--config", type=_path, default=default_config_path()
    )
    config_parser.add_argument(
        "--set", action="append", default=[], metavar="KEY=VALUE"
    )

    uninstall_parser = subparsers.add_parser(
        "uninstall", help="Remove managed hooks and local Skill Runtime files"
    )
    uninstall_parser.add_argument("--state-root", type=_path, default=None)
    uninstall_parser.add_argument(
        "--keep-data",
        action="store_true",
        help="Keep the SQLite database, queue, and configuration",
    )
    uninstall_parser.add_argument(
        "--yes", action="store_true", help="Confirm removal without prompting"
    )

    import_parser = subparsers.add_parser(
        "import", help="Import Skill runtime evidence from an observability export"
    )
    import_parser.add_argument("source", type=_path, help="JSON export path")
    import_parser.add_argument(
        "--format",
        choices=("auto",) + SUPPORTED_PROFILES,
        default="auto",
        help="Source profile; auto detects common export shapes",
    )
    import_parser.add_argument(
        "--database", type=_path, default=default_database_path()
    )

    export_parser = subparsers.add_parser(
        "export", help="Export normalized Skill evidence to an observability endpoint"
    )
    export_parser.add_argument(
        "--database", type=_path, default=default_database_path()
    )
    _otlp_args(export_parser, endpoint_required=True)

    remote_init_parser = subparsers.add_parser(
        "remote-init",
        help="Create separate permission-restricted remote viewer/ingest tokens",
    )
    remote_init_parser.add_argument(
        "--state-root", type=_path, default=default_config_path().parent
    )

    relay_parser = subparsers.add_parser(
        "relay",
        help="Replay the fail-open local Hook queue to a remote Collector",
    )
    relay_parser.add_argument(
        "--endpoint",
        default=os.environ.get("SKILL_RUNTIME_COLLECTOR_ENDPOINT", ""),
        required=not bool(os.environ.get("SKILL_RUNTIME_COLLECTOR_ENDPOINT")),
        help="Authenticated remote /api/events endpoint (HTTPS required)",
    )
    relay_parser.add_argument(
        "--token-file",
        type=_path,
        default=(
            _path(os.environ["SKILL_RUNTIME_COLLECTOR_TOKEN_FILE"])
            if os.environ.get("SKILL_RUNTIME_COLLECTOR_TOKEN_FILE")
            else None
        ),
        required=not bool(os.environ.get("SKILL_RUNTIME_COLLECTOR_TOKEN_FILE")),
        help="0600 file containing the remote ingest Bearer token",
    )
    relay_parser.add_argument(
        "--event-queue", type=_path, default=default_event_queue()
    )
    relay_parser.add_argument("--interval", type=float, default=1.0)
    relay_parser.add_argument("--timeout", type=float, default=5.0)
    relay_parser.add_argument(
        "--once", action="store_true", help="Replay one bounded batch and exit"
    )

    setup_parser = subparsers.add_parser(
        "setup",
        help="Inspect integrations; change hooks only with an explicit enable/remove flag",
    )
    setup_actions = setup_parser.add_mutually_exclusive_group()
    setup_actions.add_argument(
        "--enable-codex-hooks",
        action="store_true",
        help="Back up config and install fail-open Codex hooks",
    )
    setup_actions.add_argument(
        "--enable-claude-hooks",
        action="store_true",
        help="Back up settings and install async fail-open Claude Code hooks",
    )
    setup_actions.add_argument(
        "--remove-claude-hooks",
        action="store_true",
        help="Remove only Claude Code hooks managed by Skill Runtime",
    )
    setup_actions.add_argument(
        "--remove-codex-hooks",
        action="store_true",
        help="Remove only hooks managed by Skill Runtime",
    )
    setup_actions.add_argument(
        "--enable-qoder-hooks",
        action="store_true",
        help="Back up settings and install fail-open Qoder hooks",
    )
    setup_actions.add_argument(
        "--remove-qoder-hooks",
        action="store_true",
        help="Remove only Qoder hooks managed by Skill Runtime",
    )
    setup_actions.add_argument(
        "--enable-opencode-plugin",
        action="store_true",
        help="Install the managed, observation-only OpenCode event plugin",
    )
    setup_actions.add_argument(
        "--remove-opencode-plugin",
        action="store_true",
        help="Remove only the OpenCode plugin managed by Skill Runtime",
    )
    setup_parser.add_argument(
        "--codex-hooks",
        type=_path,
        default=Path("~/.codex/hooks.json").expanduser(),
        help="Codex hooks config path",
    )
    setup_parser.add_argument(
        "--claude-settings",
        type=_path,
        default=Path("~/.claude/settings.json").expanduser(),
        help="Claude Code settings path",
    )
    setup_parser.add_argument(
        "--qoder-settings",
        type=_path,
        default=Path("~/.qoder/settings.json").expanduser(),
        help="Qoder settings path",
    )
    setup_parser.add_argument(
        "--opencode-plugin",
        type=_path,
        default=(
            Path("~/.config/opencode/plugins/skill-runtime-intelligence.js")
            .expanduser()
        ),
        help="OpenCode managed plugin path",
    )
    setup_parser.add_argument("--executable", default="", help=argparse.SUPPRESS)

    hook_parser = subparsers.add_parser("hook", help=argparse.SUPPRESS)
    hook_parser.add_argument(
        "--agent", choices=tuple(sorted(SUPPORTED_HOOK_AGENTS)), required=True
    )
    hook_parser.add_argument(
        "--event", choices=tuple(sorted(HOOK_EVENT_TYPES)), required=True
    )
    hook_parser.add_argument(
        "--endpoint",
        default=os.environ.get(
            "SKILL_RUNTIME_COLLECTOR_ENDPOINT", DEFAULT_COLLECTOR_ENDPOINT
        ),
    )
    hook_parser.add_argument(
        "--token-file",
        type=_path,
        default=(
            _path(os.environ["SKILL_RUNTIME_COLLECTOR_TOKEN_FILE"])
            if os.environ.get("SKILL_RUNTIME_COLLECTOR_TOKEN_FILE")
            else None
        ),
    )
    hook_parser.add_argument(
        "--event-queue", type=_path, default=default_event_queue()
    )
    hook_parser.add_argument("--timeout-ms", type=int, default=150)
    hook_parser.add_argument("--managed-by", default="", help=argparse.SUPPRESS)
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    if args.command == "install":
        state_root = args.state_root
        config_path = default_config_path(state_root)
        config = (
            load_config(config_path)
            if config_path.exists()
            else default_config(state_root)
        )
        projects = [Path(value) for value in config.get("projects", [])]
        projects.append(args.project)
        config["projects"] = normalized_paths(projects)
        exclusions = [
            Path(value) for value in config.get("exclude_paths", [])
        ]
        exclusions.extend(args.exclude)
        config["exclude_paths"] = normalized_paths(exclusions)
        database = Path(config["database"]).expanduser()
        executable = args.executable or _current_executable()
        native_sender = install_native_hook_sender(state_root)
        integrations = [
            inspect_codex_integration(
                executable=executable, state_root=state_root
            ),
            inspect_claude_integration(
                executable=executable, state_root=state_root
            ),
            inspect_qoder_integration(
                executable=executable, state_root=state_root
            ),
            inspect_opencode_integration(
                executable=executable, state_root=state_root
            ),
        ]
        detected = [item for item in integrations if item["detected"]]
        enable_hooks = args.enable_hooks
        if (
            not enable_hooks
            and not args.no_hooks
            and detected
            and sys.stdin.isatty()
        ):
            names = ", ".join(item["agent"] for item in detected)
            answer = input(
                f"Enable async/fail-open runtime hooks for {names}? [y/N] "
            ).strip().lower()
            enable_hooks = answer in {"y", "yes"}
        hook_results = []
        config.setdefault("hooks", {})
        for integration in detected:
            agent = integration["agent"]
            if enable_hooks:
                try:
                    if agent == "codex":
                        result = enable_codex_hooks(
                            executable, state_root=state_root
                        )
                    elif agent == "claude-code":
                        result = enable_claude_hooks(
                            executable, state_root=state_root
                        )
                    elif agent == "qoder":
                        result = enable_qoder_hooks(
                            executable, state_root=state_root
                        )
                    else:
                        result = enable_opencode_plugin(
                            executable, state_root=state_root
                        )
                    hook_results.append({"agent": agent, **result})
                    config["hooks"][agent] = {"consent": "granted"}
                except IntegrationError as exc:
                    hook_results.append(
                        {
                            "agent": agent,
                            "changed": False,
                            "error": str(exc),
                        }
                    )
                    config["hooks"][agent] = {
                        "consent": "granted",
                        "status": "configuration_failed",
                    }
            elif args.no_hooks:
                config["hooks"][agent] = {"consent": "declined"}
        save_config(config, config_path)
        roots = []
        for project in config["projects"]:
            roots.extend(default_skill_roots(Path(project)))
        indexed = index_local(
            database,
            args.codex_sessions,
            roots,
            [Path(value) for value in config["exclude_paths"]],
        )
        integrations = [
            inspect_codex_integration(executable=executable, state_root=state_root),
            inspect_claude_integration(executable=executable, state_root=state_root),
            inspect_qoder_integration(executable=executable, state_root=state_root),
            inspect_opencode_integration(executable=executable, state_root=state_root),
        ]
        result = {
            "installed": True,
            "config_path": str(config_path),
            "database": str(database),
            "projects": config["projects"],
            "excluded_paths": config["exclude_paths"],
            "integrations": integrations,
            "hooks": hook_results,
            "native_hook_sender": native_sender,
            "consent_required": [
                item["agent"]
                for item in detected
                if not enable_hooks and not args.no_hooks
            ],
            "index": indexed,
            "next": "skill-runtime start",
            "codex_trust_required": bool(
                enable_hooks
                and any(item["agent"] == "codex" for item in detected)
            ),
            "codex_trust_action": (
                "In Codex, run `/hooks`, review the exact Skill Runtime commands, "
                "and trust them. Then start a new turn and run `skill-runtime doctor`."
                if enable_hooks
                else ""
            ),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "index":
        _run_index(args)
    elif args.command == "serve":
        _apply_runtime_config(args)
        remote_access = _remote_access_from_args(args)
        _start_queue_watcher(args)
        _start_otlp_exporter(args)
        _start_retention_worker(args)
        _schedule_browser(args)
        serve(
            args.database,
            args.host,
            args.port,
            event_queue=args.event_queue,
            hook_socket=args.hook_socket,
            config_path=args.config,
            remote_access=remote_access,
        )
    elif args.command == "dev":
        _apply_runtime_config(args)
        _run_live_runtime(args)
    elif args.command == "start":
        _apply_runtime_config(args)
        _remote_access_from_args(args)
        if args.foreground:
            _run_live_runtime(args, index_first=False)
        else:
            if args.remote and args.tls_cert:
                raise SystemExit(
                    "direct-TLS remote mode must run with --foreground under a "
                    "service manager; managed background health probing supports "
                    "the loopback --behind-https-proxy mode"
                )
            if args.otlp_header:
                raise SystemExit(
                    "Do not put exporter secrets in daemon arguments. "
                    "Use OTEL_EXPORTER_OTLP_HEADERS in the environment."
                )
            result = start_runtime(
                _background_command(args),
                state_root=args.state_root,
                host=args.host,
                port=args.port,
            )
            _open_runtime(args)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "stop":
        result = stop_runtime(args.state_root, args.host, args.port)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "status":
        print(
            json.dumps(
                runtime_status(args.state_root, args.host, args.port),
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "restart":
        result = restart_runtime(args.state_root, args.host, args.port)
        if not args.no_open:
            webbrowser.open(result["url"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "doctor":
        result = diagnose_runtime(
            state_root=args.state_root,
            host=args.host,
            port=args.port,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result["ok"]:
            raise SystemExit(1)
    elif args.command == "config":
        config = load_config(args.config)
        for assignment in args.set:
            _set_config_value(config, assignment)
        if args.set:
            save_config(config, args.config)
        print(json.dumps(config, ensure_ascii=False, indent=2))
    elif args.command == "uninstall":
        root = (args.state_root or default_config_path().parent).expanduser()
        config_path = default_config_path(root)
        try:
            installation_config = (
                load_config(config_path) if config_path.exists() else {}
            )
            config_error = ""
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            installation_config = {}
            config_error = str(exc)
        if not args.yes:
            if not sys.stdin.isatty():
                raise SystemExit("uninstall requires --yes in a non-interactive shell")
            answer = input(
                f"Remove managed hooks and Skill Runtime state under {root}? [y/N] "
            ).strip().lower()
            if answer not in {"y", "yes"}:
                raise SystemExit("Uninstall cancelled")
        stopped = stop_runtime(args.state_root)
        hook_results = []
        for agent, remover in (
            ("codex", remove_codex_hooks),
            ("claude-code", remove_claude_hooks),
            ("qoder", remove_qoder_hooks),
            ("opencode", remove_opencode_plugin),
        ):
            consent = (
                installation_config.get("hooks", {})
                .get(agent, {})
                .get("consent")
            )
            if consent != "granted":
                hook_results.append(
                    {
                        "agent": agent,
                        "changed": False,
                        "skipped": True,
                        "reason": (
                            "installation_config_unreadable"
                            if config_error
                            else "not_owned_by_this_installation"
                        ),
                        "consent": consent or "not_recorded",
                    }
                )
                continue
            try:
                hook_results.append({"agent": agent, **remover(state_root=args.state_root)})
            except IntegrationError as exc:
                hook_results.append({"agent": agent, "error": str(exc)})
        removed_paths = []
        if root.exists() and args.keep_data:
            for child in ("bin", "run", "logs", "integrations"):
                target = root / child
                if target.exists():
                    shutil.rmtree(target)
                    removed_paths.append(str(target))
        elif root.exists():
            _safe_remove_state_root(root)
            removed_paths.append(str(root))
        print(
            json.dumps(
                {
                    "uninstalled": True,
                    "runtime": stopped,
                    "hooks": hook_results,
                    "removed_paths": removed_paths,
                    "data_kept": args.keep_data,
                    "agent_source_files_modified": False,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    elif args.command == "import":
        result = import_observability(args.database, args.source, args.format)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "export":
        result = export_otlp_once(
            args.database,
            args.otlp_endpoint,
            headers=_parse_headers(args.otlp_header),
            batch_size=args.otlp_batch_size,
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "remote-init":
        result = initialize_remote_secrets(args.state_root)
        result["next"] = (
            "Expose the loopback backend through an authenticated HTTPS proxy, "
            "then run `skill-runtime serve --remote --behind-https-proxy`."
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "relay":
        endpoint = _validated_relay_endpoint(args.endpoint)
        token = read_secret_file(args.token_file)
        if args.once:
            result = drain_remote_event_queue(
                endpoint,
                token,
                args.event_queue,
                timeout_seconds=max(0.05, args.timeout),
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(
                "Relaying the local fail-open queue to the authenticated remote "
                "Collector; press Ctrl-C to stop."
            )
            try:
                watch_remote_event_queue(
                    endpoint,
                    token,
                    args.event_queue,
                    interval_seconds=max(0.25, args.interval),
                    timeout_seconds=max(0.05, args.timeout),
                )
            except KeyboardInterrupt:
                pass
    elif args.command == "setup":
        executable = args.executable or _current_executable()
        native_sender = None
        if args.enable_codex_hooks:
            native_sender = build_native_hook_sender()
            result = enable_codex_hooks(executable, args.codex_hooks)
        elif args.remove_codex_hooks:
            result = remove_codex_hooks(args.codex_hooks)
        elif args.enable_claude_hooks:
            native_sender = build_native_hook_sender()
            result = enable_claude_hooks(executable, args.claude_settings)
        elif args.remove_claude_hooks:
            result = remove_claude_hooks(args.claude_settings)
        elif args.enable_qoder_hooks:
            native_sender = build_native_hook_sender()
            result = enable_qoder_hooks(executable, args.qoder_settings)
        elif args.remove_qoder_hooks:
            result = remove_qoder_hooks(args.qoder_settings)
        elif args.enable_opencode_plugin:
            native_sender = build_native_hook_sender()
            result = enable_opencode_plugin(executable, args.opencode_plugin)
        elif args.remove_opencode_plugin:
            result = remove_opencode_plugin(args.opencode_plugin)
        else:
            result = {
                "integrations": [
                    inspect_codex_integration(args.codex_hooks, executable),
                    inspect_claude_integration(args.claude_settings, executable),
                    inspect_qoder_integration(args.qoder_settings, executable),
                    inspect_opencode_integration(args.opencode_plugin, executable),
                ]
            }
        if native_sender is not None:
            result["native_hook_sender"] = native_sender
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "hook":
        _run_hook(args)
