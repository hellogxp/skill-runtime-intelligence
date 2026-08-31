"""Local or explicitly authenticated self-hosted HTTP API and web UI."""

import json
import mimetypes
import shutil
import ssl
import sys
import threading
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
from .datav import build_datav_datasets
from .integrations import (
    IntegrationError,
    enable_claude_hooks,
    enable_codex_hooks,
    enable_opencode_plugin,
    enable_qoder_hooks,
    enable_qoderwork_hooks,
    inspect_claude_integration,
    inspect_codex_integration,
    inspect_opencode_integration,
    inspect_qoder_integration,
    inspect_qoderwork_integration,
)
from .native_sender import build_native_hook_sender
from .hook_bridge import HookBridge, default_hook_socket
from .remote_access import (
    RemoteAccess,
    ingest_authorized,
    is_loopback_host,
    viewer_authorized,
)
from .diagnosis_engine import build_diagnosis_payload
from .storage import Storage


MAX_EVENT_BODY_BYTES = 1024 * 1024
LIVE_STREAM_LOCK = threading.Lock()
LIVE_STREAM_TOKENS = []
MAX_LIVE_STREAMS = 2


def _runtime_executable() -> str:
    candidate = Path(sys.argv[0]).expanduser()
    if candidate.exists() and (
        candidate.name in {"skill-runtime", "skill-panorama"}
        or candidate.suffix == ".pyz"
    ):
        return str(candidate.resolve())
    return shutil.which("skill-runtime") or ""


def _record_hook_consent(
    config: dict,
    agent: str,
    result: dict,
) -> None:
    state = config.setdefault("hooks", {}).setdefault(agent, {})
    state["consent"] = "granted"
    state["status"] = (
        "configuration_failed" if result.get("error") else "configured"
    )


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
            remote = self._remote_access()
            if remote.enabled and not self._viewer_credentials_valid():
                self._json(
                    {
                        "ok": True,
                        "product": "skill-runtime-intelligence",
                        "version": __version__,
                        "local": False,
                        "deployment": "self_hosted_remote",
                        "auth_required": True,
                        "transport": remote.transport,
                    }
                )
                return
            self._with_storage(
                lambda storage: self._json(
                    {
                        "ok": True,
                        "product": "skill-runtime-intelligence",
                        "version": __version__,
                        "local": not remote.enabled,
                        "deployment": (
                            "self_hosted_remote" if remote.enabled else "local"
                        ),
                        "auth_required": remote.enabled,
                        "transport": remote.transport,
                        "revision": storage.revision(),
                        "counts": storage.counts(),
                    }
                )
            )
            return
        if not self._authorize_viewer():
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
            config_path = self.server.config_path  # type: ignore[attr-defined]
            try:
                integration_config = load_config(config_path)
            except (OSError, ValueError, json.JSONDecodeError):
                integration_config = {"hooks": {}}
            integration_state_root = config_path.expanduser().resolve().parent

            def integrations(storage: Storage) -> None:
                sources = storage.list_sources()
                result = []
                for agent, inspector in (
                    ("codex", inspect_codex_integration),
                    ("claude-code", inspect_claude_integration),
                    ("qoder", inspect_qoder_integration),
                    ("qoderwork", inspect_qoderwork_integration),
                    ("opencode", inspect_opencode_integration),
                ):
                    try:
                        item = inspector(state_root=integration_state_root)
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
                    item["consent"] = (
                        integration_config.get("hooks", {})
                        .get(agent, {})
                        .get("consent", "not_requested")
                    )
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
        if path == "/api/datav" or path.startswith("/api/datav/"):
            dataset = (
                path[len("/api/datav/"):]
                if path.startswith("/api/datav/")
                else "manifest"
            )
            if dataset not in {"manifest", "summary", "boundaries", "skills", "runs"}:
                self._json({"error": "DataV dataset not found"}, HTTPStatus.NOT_FOUND)
                return
            parameters = parse_qs(urlparse(self.path).query)
            try:
                limit = int((parameters.get("limit") or ["300"])[0])
            except ValueError:
                self._json({"error": "limit must be an integer"}, HTTPStatus.BAD_REQUEST)
                return

            def datav(storage: Storage) -> None:
                datasets = build_datav_datasets(storage, limit=limit)
                self._json(datasets[dataset])

            self._with_storage(datav)
            return
        if path == "/api/skill-runs":
            parameters = parse_qs(urlparse(self.path).query)
            try:
                limit = int((parameters.get("limit") or ["25"])[0])
            except ValueError:
                self._json({"error": "limit must be an integer"}, HTTPStatus.BAD_REQUEST)
                return
            if limit < 1 or limit > 100:
                self._json(
                    {"error": "limit must be between 1 and 100"},
                    HTTPStatus.BAD_REQUEST,
                )
                return

            def list_skill_run_page(storage: Storage) -> None:
                try:
                    result = storage.list_skill_runs_page(
                        limit=limit,
                        cursor=(parameters.get("cursor") or [""])[0],
                        query=(parameters.get("q") or [""])[0].strip(),
                        status=(parameters.get("status") or [""])[0],
                        agent=(parameters.get("agent") or [""])[0],
                        project=(parameters.get("project") or [""])[0],
                        skill=(parameters.get("skill") or [""])[0],
                        evidence_grade=(parameters.get("grade") or [""])[0],
                        date=(parameters.get("date") or [""])[0],
                        errors_only=(parameters.get("errors") or ["false"])[0].lower() == "true",
                    )
                except ValueError as exc:
                    self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
                    return
                result["facets_url"] = "/api/skill-run-facets"
                self._json(result)

            self._with_storage(list_skill_run_page)
            return
        if path == "/api/skill-run-facets":
            self._with_storage(
                lambda storage: self._json(storage.skill_run_facets())
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
                remote = self._remote_access()
                self._json(
                    {
                        "config": config,
                        "config_path": str(config_path),
                        "database": str(database),
                        "database_bytes": (
                            database.stat().st_size if database.exists() else 0
                        ),
                        "counts": storage.counts(),
                        "deployment": {
                            "mode": (
                                "self_hosted_remote" if remote.enabled else "local"
                            ),
                            "transport": remote.transport,
                            "viewer_read_only": remote.enabled,
                            "observability_interoperability_optional": True,
                        },
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
        if path == "/api/events":
            if not self._authorize_ingest():
                return
        elif not self._authorize_viewer():
            return
        elif self._remote_access().enabled:
            self._forbidden("Remote viewer credentials are read-only")
            return
        if path == "/api/integrations/enable":
            try:
                payload = self._read_json_body(MAX_EVENT_BODY_BYTES)
                agent = str(payload.get("agent") or "").strip().lower()
                operations = {
                    "codex": (inspect_codex_integration, enable_codex_hooks),
                    "claude-code": (
                        inspect_claude_integration,
                        enable_claude_hooks,
                    ),
                    "qoder": (inspect_qoder_integration, enable_qoder_hooks),
                    "qoderwork": (
                        inspect_qoderwork_integration,
                        enable_qoderwork_hooks,
                    ),
                    "opencode": (
                        inspect_opencode_integration,
                        enable_opencode_plugin,
                    ),
                }
                if agent not in operations:
                    raise ValueError("unsupported Agent integration")
                executable = _runtime_executable()
                if not executable:
                    raise ValueError(
                        "Unable to locate the skill-runtime executable; "
                        "run the corresponding `skill-runtime setup` command."
                    )
                config_path = self.server.config_path  # type: ignore[attr-defined]
                config = load_config(config_path)
                state_root = config_path.expanduser().resolve().parent
                inspector, enable = operations[agent]
                inspected = inspector(
                    executable=executable,
                    state_root=state_root,
                )
                if not inspected.get("detected"):
                    raise ValueError(f"{agent} is not detected on this machine")
                native_sender = build_native_hook_sender(state_root)
                result = enable(executable, state_root=state_root)
                _record_hook_consent(config, agent, result)
                save_config(config, config_path)
                self._json(
                    {
                        "ok": True,
                        "agent": agent,
                        "integration": result,
                        "native_hook_sender": native_sender,
                        "next": (
                            "Restart or open a new Agent session, then run "
                            "`skill-runtime doctor`."
                        ),
                    }
                )
            except (
                CollectorValidationError,
                IntegrationError,
                json.JSONDecodeError,
                UnicodeDecodeError,
                OSError,
                TypeError,
                ValueError,
            ) as exc:
                self._json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return
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
        if path == "/api/diagnose":
            # Stateless projection endpoint. A remote host that already holds
            # normalized events calls this so the diagnosis semantics have one
            # implementation instead of being reimplemented per product.
            try:
                payload = self._read_json_body(MAX_EVENT_BODY_BYTES)
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._json({"error": "Invalid JSON body"}, HTTPStatus.BAD_REQUEST)
                return
            if not isinstance(payload, dict):
                self._json(
                    {"error": "Body must be a JSON object"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            run = payload.get("run")
            if not isinstance(run, dict) or not run.get("name"):
                self._json(
                    {"error": "run object with a name is required"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            events = payload.get("events")
            if events is None:
                events = run.get("events")
            if events is not None and not isinstance(events, list):
                self._json(
                    {"error": "events must be an array"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            capabilities = payload.get("capabilities")
            if not isinstance(capabilities, dict):
                # Fall back to the declared matrix for the named adapter so an
                # unknown adapter stays 'unsupported' instead of assumed good.
                capabilities = Storage.capabilities_for(
                    str(run.get("adapter") or "otel")
                )
            source_content = payload.get("skill_source_content")
            if source_content is not None and not isinstance(source_content, str):
                self._json(
                    {"error": "skill_source_content must be a string"},
                    HTTPStatus.BAD_REQUEST,
                )
                return
            try:
                result = build_diagnosis_payload(
                    run,
                    capabilities=capabilities,
                    events=events,
                    skill_source_content=source_content,
                )
            except (KeyError, TypeError, ValueError) as exc:
                self._json(
                    {"error": f"Unprocessable run: {exc}"},
                    HTTPStatus.UNPROCESSABLE_ENTITY,
                )
                return
            self._json(result, HTTPStatus.OK)
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
        if not self._authorize_viewer():
            return
        if self._remote_access().enabled:
            self._forbidden("Remote viewer credentials are read-only")
            return
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

    def _remote_access(self) -> RemoteAccess:
        return self.server.remote_access  # type: ignore[attr-defined]

    def _viewer_credentials_valid(self) -> bool:
        remote = self._remote_access()
        return not remote.enabled or viewer_authorized(
            self.headers.get("Authorization", ""), remote.viewer_token
        )

    def _authorize_viewer(self) -> bool:
        if self._viewer_credentials_valid():
            return True
        self._unauthorized('Basic realm="Skill Runtime Intelligence", charset="UTF-8"')
        return False

    def _authorize_ingest(self) -> bool:
        remote = self._remote_access()
        if not remote.enabled or ingest_authorized(
            self.headers.get("Authorization", ""), remote.ingest_token
        ):
            return True
        self._unauthorized('Bearer realm="Skill Runtime Intelligence Collector"')
        return False

    def _unauthorized(self, challenge: str) -> None:
        body = json.dumps({"error": "Authentication required"}).encode("utf-8")
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", challenge)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _forbidden(self, message: str) -> None:
        self._json({"error": message}, HTTPStatus.FORBIDDEN)

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
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy", "default-src 'self'; style-src 'self'"
        )

    def _stream_revisions(self) -> None:
        stream_client = (
            parse_qs(urlparse(self.path).query).get("client") or [""]
        )[0]
        current_client = stream_client == "live-v3"
        stream_token = object() if current_client else None
        if stream_token is not None:
            with LIVE_STREAM_LOCK:
                LIVE_STREAM_TOKENS.append(stream_token)
                del LIVE_STREAM_TOKENS[:-MAX_LIVE_STREAMS]
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.send_header("Connection", "keep-alive" if current_client else "close")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        last_revision = -1
        last_heartbeat = 0.0
        # Old pages opened before the live-v3 rollout reconnect to their
        # unversioned URL forever. Give those streams a short lease and a
        # longer retry delay so stale tabs cannot monopolize the browser's
        # per-origin HTTP/1.1 connection pool. Current visible pages use the
        # older stream forever. Give them a short lease; current visible pages
        # retain the normal long-lived realtime path.
        deadline = time.monotonic() + (55.0 if current_client else 3.0)
        storage = Storage(self.server.database_path)  # type: ignore[attr-defined]
        try:
            retry_ms = 1500 if current_client else 5000
            self.wfile.write(f"retry: {retry_ms}\n\n".encode("ascii"))
            self.wfile.flush()
            while time.monotonic() < deadline:
                if stream_token is not None:
                    with LIVE_STREAM_LOCK:
                        if stream_token not in LIVE_STREAM_TOKENS:
                            break
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
            if stream_token is not None:
                with LIVE_STREAM_LOCK:
                    if stream_token in LIVE_STREAM_TOKENS:
                        LIVE_STREAM_TOKENS.remove(stream_token)
            if not current_client:
                self.close_connection = True

    def _static(self, path: str) -> None:
        filename = {
            "/": "index.html",
            "/index.html": "index.html",
            "/locale-packs.js": "locale-packs.js",
            "/i18n.js": "i18n.js",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
            "/runtime-detail-v2.css": "runtime-detail-v2.css",
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
        versioned = bool(parse_qs(urlparse(self.path).query).get("v"))
        self.send_header(
            "Cache-Control",
            "public, max-age=31536000, immutable"
            if versioned else "no-cache, no-store, must-revalidate",
        )
        self._security_headers()
        self.end_headers()
        self.wfile.write(content)


def create_server(
    database: Path,
    host: str = "127.0.0.1",
    port: int = 4317,
    config_path: Path = None,
    remote_access: RemoteAccess = None,
) -> ThreadingHTTPServer:
    access = remote_access or RemoteAccess()
    if not access.enabled and not is_loopback_host(host):
        raise ValueError("non-loopback server binding requires remote access policy")
    if access.enabled and (
        not access.viewer_token
        or not access.ingest_token
        or (not access.direct_tls and not access.behind_https_proxy)
    ):
        raise ValueError("remote access policy is incomplete")
    if access.behind_https_proxy and not is_loopback_host(host):
        raise ValueError("HTTPS proxy backends must bind to loopback")
    server = ThreadingHTTPServer((host, port), PanoramaHandler)
    server.daemon_threads = True
    server.database_path = database.expanduser().resolve()  # type: ignore[attr-defined]
    server.config_path = (  # type: ignore[attr-defined]
        config_path or default_config_path()
    ).expanduser().resolve()
    server.remote_access = access  # type: ignore[attr-defined]
    if access.direct_tls:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(
            certfile=str(access.tls_cert),
            keyfile=str(access.tls_key),
        )
        server.socket = context.wrap_socket(server.socket, server_side=True)
    return server


def serve(
    database: Path,
    host: str = "127.0.0.1",
    port: int = 4317,
    event_queue: Path = None,
    hook_socket: Path = None,
    config_path: Path = None,
    remote_access: RemoteAccess = None,
) -> None:
    access = remote_access or RemoteAccess()
    warm_storage = Storage(database)
    try:
        warm_storage.warm_skill_run_summary()
    finally:
        warm_storage.close()
    server = create_server(database, host, port, config_path, access)
    bridge = HookBridge(
        database,
        socket_path=hook_socket or default_hook_socket(),
        queue_path=event_queue,
    ).start()
    scheme = "https" if access.direct_tls else "http"
    print(f"Skill Runtime Intelligence: {scheme}://{host}:{port}")
    print(f"Database: {server.database_path}")
    print(f"Hook bridge: {bridge.socket_path}")
    if access.enabled:
        print(
            "Authenticated self-hosted remote service "
            f"({access.transport}); press Ctrl-C to stop."
        )
    else:
        print("Loopback-only local service. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        bridge.close()
        server.server_close()
