"""Local-only HTTP API and web application."""

import json
import mimetypes
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import __version__
from .config import (
    default_config_path,
    load_config,
    normalized_paths,
    save_config,
)
from .collector import (
    CollectorValidationError,
    EVENT_STAGES,
    VALID_COLLECTION_MODES,
    normalize_collector_payload,
)
from .integrations import (
    IntegrationError,
    inspect_claude_integration,
    inspect_codex_integration,
    inspect_opencode_integration,
    inspect_qoder_integration,
)
from .hook_bridge import HookBridge, default_hook_socket
from .storage import Storage


MAX_EVENT_BODY_BYTES = 1024 * 1024


class PanoramaHandler(BaseHTTPRequestHandler):
    server_version = f"SkillRuntime/{__version__}"

    def handle(self) -> None:
        try:
            super().handle()
        except ConnectionResetError:
            # Browsers reconnect SSE streams by design; a closed client socket
            # is not a Collector or runtime failure.
            return

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/api/health":
            self._with_storage(
                lambda storage: self._json(
                    {
                        "ok": True,
                        "product": "skill-runtime-intelligence",
                        "version": __version__,
                        "local": True,
                        "revision": storage.revision(),
                        "counts": storage.counts(),
                    }
                )
            )
            return
        if path == "/api/stream":
            self._stream_revisions()
            return
        if path == "/api/collector/schema":
            self._json(
                {
                    "version": "runtime-envelope-v1",
                    "endpoint": "/api/events",
                    "max_body_bytes": MAX_EVENT_BODY_BYTES,
                    "collection_modes": sorted(VALID_COLLECTION_MODES),
                    "event_types": sorted(EVENT_STAGES),
                }
            )
            return
        if path == "/api/integrations":
            def integrations(storage: Storage) -> None:
                sources = storage.list_sources()
                result = []
                for agent, inspector in (
                    ("codex", inspect_codex_integration),
                    ("claude-code", inspect_claude_integration),
                    ("qoder", inspect_qoder_integration),
                    ("opencode", inspect_opencode_integration),
                ):
                    try:
                        item = inspector()
                    except IntegrationError as exc:
                        item = {
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
                    item["live_evidence_seen"] = bool(observed)
                    item["live_evidence"] = observed
                    if observed:
                        item["connection_status"] = "verified"
                    elif item.get("installed"):
                        item["connection_status"] = (
                            "awaiting_agent_trust_or_new_run"
                        )
                    elif item.get("detected"):
                        item["connection_status"] = "not_configured"
                    else:
                        item["connection_status"] = "not_detected"
                    result.append(item)
                self._json({"integrations": result})

            self._with_storage(integrations)
            return
        if path == "/api/exporters":
            def exporters(storage: Storage) -> None:
                result = []
                for item in storage.list_runtime_state("export.otlp."):
                    if not item["key"].endswith(".status"):
                        continue
                    try:
                        status = json.loads(item["value"])
                    except (TypeError, json.JSONDecodeError):
                        continue
                    status["updated_at"] = item["updated_at"]
                    result.append(status)
                self._json({"exporters": result})

            self._with_storage(exporters)
            return
        if path == "/api/skill-runs":
            self._with_storage(
                lambda storage: self._json(
                    {"skill_runs": storage.list_skill_runs()}
                )
            )
            return
        if path == "/api/compare":
            parameters = parse_qs(urlparse(self.path).query)
            left = (parameters.get("left") or [""])[0]
            right = (parameters.get("right") or [""])[0]
            axis = (parameters.get("axis") or ["same_skill"])[0]
            task_aligned = (
                (parameters.get("aligned") or ["false"])[0].lower() == "true"
            )
            if not left or not right:
                self._json(
                    {"error": "left and right SkillRun IDs are required"},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            def compare(storage: Storage) -> None:
                result = storage.compare_skill_runs(
                    left,
                    right,
                    axis=axis,
                    task_aligned=task_aligned,
                )
                if result is None:
                    self._json(
                        {"error": "SkillRun not found"}, HTTPStatus.NOT_FOUND
                    )
                else:
                    self._json(result)

            self._with_storage(compare)
            return
        if path.startswith("/api/skill-runs/"):
            skill_run_id = unquote(path[len("/api/skill-runs/"):])

            def get_skill_run(storage: Storage) -> None:
                run = storage.get_skill_run(skill_run_id)
                if run is None:
                    self._json({"error": "SkillRun not found"}, HTTPStatus.NOT_FOUND)
                else:
                    self._json(run)

            self._with_storage(get_skill_run)
            return
        if path == "/api/sources":
            self._with_storage(
                lambda storage: self._json({"sources": storage.list_sources()})
            )
            return
        if path == "/api/runs":
            self._with_storage(lambda storage: self._json({"runs": storage.list_runs()}))
            return
        if path.startswith("/api/runs/"):
            session_id = unquote(path[len("/api/runs/"):])

            def get_run(storage: Storage) -> None:
                run = storage.get_run(session_id)
                if run is None:
                    self._json({"error": "Run not found"}, HTTPStatus.NOT_FOUND)
                else:
                    self._json(run)

            self._with_storage(get_run)
            return
        if path == "/api/skills":
            self._with_storage(lambda storage: self._json({"skills": storage.list_skills()}))
            return
        if path == "/api/skill-conflicts":
            self._with_storage(
                lambda storage: self._json(
                    {
                        "conflicts": storage.skill_conflicts(),
                        "evidence_grade": "inferred",
                    }
                )
            )
            return
        if path == "/api/skill-compare":
            parameters = parse_qs(urlparse(self.path).query)
            left = (parameters.get("left") or [""])[0]
            right = (parameters.get("right") or [""])[0]
            if not left or not right:
                self._json(
                    {"error": "left and right Skill IDs are required"},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            def compare_skills(storage: Storage) -> None:
                result = storage.compare_skill_definitions(left, right)
                if result is None:
                    self._json(
                        {"error": "Skill definition not found"},
                        HTTPStatus.NOT_FOUND,
                    )
                else:
                    self._json(result)

            self._with_storage(compare_skills)
            return
        if path.startswith("/api/skills/"):
            skill_id = unquote(path[len("/api/skills/"):])

            def get_skill(storage: Storage) -> None:
                skill = storage.get_skill(skill_id)
                if skill is None:
                    self._json({"error": "Skill not found"}, HTTPStatus.NOT_FOUND)
                else:
                    self._json(skill)

            self._with_storage(get_skill)
            return
        if path == "/api/settings":
            config_path = self.server.config_path  # type: ignore[attr-defined]
            try:
                config = load_config(config_path)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                self._json(
                    {"error": f"Invalid local config: {exc}"},
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                )
                return

            def settings(storage: Storage) -> None:
                database = self.server.database_path  # type: ignore[attr-defined]
                self._json(
                    {
                        "config": config,
                        "config_path": str(config_path),
                        "database": str(database),
                        "database_bytes": (
                            database.stat().st_size if database.exists() else 0
                        ),
                        "counts": storage.counts(),
                        "privacy": {
                            "raw_agent_files_modified": False,
                            "model_requests_proxied": False,
                            "network_export_opt_in": True,
                            "raw_prompt_exported": False,
                        },
                    }
                )

            self._with_storage(settings)
            return
        self._static(path)

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/api/settings":
            try:
                payload = self._read_json_body(MAX_EVENT_BODY_BYTES)
                config_path = self.server.config_path  # type: ignore[attr-defined]
                config = load_config(config_path)
                if "projects" in payload:
                    config["projects"] = normalized_paths(
                        Path(value) for value in payload["projects"]
                    )
                if "exclude_paths" in payload:
                    config["exclude_paths"] = normalized_paths(
                        Path(value) for value in payload["exclude_paths"]
                    )
                if "retention_days" in payload:
                    retention = payload["retention_days"]
                    if retention is not None:
                        retention = int(retention)
                        if retention < 1 or retention > 3650:
                            raise ValueError(
                                "retention_days must be null or between 1 and 3650"
                            )
                    config["retention_days"] = retention
                saved = save_config(config, config_path)
                self._json(
                    {
                        "ok": True,
                        "config": config,
                        "config_path": str(saved),
                        "restart_required": True,
                    }
                )
            except (
                CollectorValidationError,
                json.JSONDecodeError,
                UnicodeDecodeError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
        if path != "/api/events":
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        try:
            payload = self._read_json_body(MAX_EVENT_BODY_BYTES)
            bundles = normalize_collector_payload(payload)
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
            return
        except CollectorValidationError as exc:
            self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        def ingest(storage: Storage) -> None:
            result = storage.append_collector_events(bundles)
            result["revision"] = storage.revision()
            result["ok"] = True
            result["event_ids"] = [bundle["event"]["event_id"] for bundle in bundles]
            result["session_ids"] = sorted(
                {bundle["event"]["session_id"] for bundle in bundles}
            )
            result["skill_run_ids"] = sorted(
                {
                    bundle["event"]["skill_run_id"]
                    for bundle in bundles
                    if bundle["event"].get("skill_run_id")
                }
            )
            status = (
                HTTPStatus.ACCEPTED
                if result["accepted"]
                else HTTPStatus.OK
            )
            self._json(result, status)

        self._with_storage(ingest)

    def do_DELETE(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if not path.startswith("/api/skill-runs/"):
            self._json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        skill_run_id = unquote(path[len("/api/skill-runs/"):])

        def delete(storage: Storage) -> None:
            result = storage.delete_skill_run(skill_run_id)
            if result is None:
                self._json({"error": "SkillRun not found"}, HTTPStatus.NOT_FOUND)
            else:
                self._json({"ok": True, **result})

        self._with_storage(delete)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {self.address_string()} {fmt % args}")

    def _with_storage(self, operation) -> None:
        storage = Storage(self.server.database_path)  # type: ignore[attr-defined]
        try:
            operation(storage)
        finally:
            storage.close()

    def _read_json_body(self, maximum: int):
        content_type = self.headers.get("Content-Type", "")
        if not content_type.lower().startswith("application/json"):
            raise CollectorValidationError(
                "Content-Type must be application/json"
            )
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise CollectorValidationError("Invalid Content-Length") from exc
        if content_length <= 0:
            raise CollectorValidationError("Request body is required")
        if content_length > maximum:
            raise CollectorValidationError("Request body is too large")
        return json.loads(self.rfile.read(content_length))

    def _json(self, value, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _stream_revisions(self) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last_revision = -1
        last_heartbeat = 0.0
        deadline = time.monotonic() + 55.0
        storage = Storage(self.server.database_path)  # type: ignore[attr-defined]
        try:
            self.wfile.write(b"retry: 1500\n\n")
            self.wfile.flush()
            while time.monotonic() < deadline:
                revision = storage.revision()
                now = time.monotonic()
                if revision != last_revision:
                    body = json.dumps(
                        {"revision": revision}, separators=(",", ":")
                    ).encode("utf-8")
                    self.wfile.write(b"event: revision\n")
                    self.wfile.write(b"data: " + body + b"\n\n")
                    self.wfile.flush()
                    last_revision = revision
                    last_heartbeat = now
                elif now - last_heartbeat >= 15.0:
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    last_heartbeat = now
                time.sleep(0.75)
        except (BrokenPipeError, ConnectionResetError):
            return
        finally:
            storage.close()

    def _static(self, path: str) -> None:
        filename = {
            "/": "index.html",
            "/index.html": "index.html",
            "/locale-packs.js": "locale-packs.js",
            "/i18n.js": "i18n.js",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
            "/favicon.svg": "favicon.svg",
        }.get(path)
        if not filename:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = resources.files("skill_runtime_intelligence.web").joinpath(filename).read_bytes()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(content)


def create_server(
    database: Path,
    host: str = "127.0.0.1",
    port: int = 4317,
    config_path: Path = None,
) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), PanoramaHandler)
    server.daemon_threads = True
    server.database_path = database.expanduser().resolve()  # type: ignore[attr-defined]
    server.config_path = (  # type: ignore[attr-defined]
        config_path or default_config_path()
    ).expanduser().resolve()
    return server


def serve(
    database: Path,
    host: str = "127.0.0.1",
    port: int = 4317,
    event_queue: Path = None,
    hook_socket: Path = None,
    config_path: Path = None,
) -> None:
    server = create_server(database, host, port, config_path)
    bridge = HookBridge(
        database,
        socket_path=hook_socket or default_hook_socket(),
        queue_path=event_queue,
    ).start()
    print(f"Skill Runtime Intelligence: http://{host}:{port}")
    print(f"Database: {server.database_path}")
    print(f"Hook bridge: {bridge.socket_path}")
    print("Local-only server. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        server.server_close()
