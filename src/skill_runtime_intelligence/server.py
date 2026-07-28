"""Local-only HTTP API and web application."""

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from urllib.parse import unquote, urlparse

from .storage import Storage


class PanoramaHandler(BaseHTTPRequestHandler):
    server_version = "SkillRuntime/0.1"

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        path = urlparse(self.path).path
        if path == "/api/health":
            self._with_storage(
                lambda storage: self._json(
                    {"ok": True, "local": True, "counts": storage.counts()}
                )
            )
            return
        if path == "/api/skill-runs":
            self._with_storage(
                lambda storage: self._json(
                    {"skill_runs": storage.list_skill_runs()}
                )
            )
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
        self._static(path)

    def log_message(self, fmt: str, *args) -> None:
        print(f"[web] {self.address_string()} {fmt % args}")

    def _with_storage(self, operation) -> None:
        storage = Storage(self.server.database_path)  # type: ignore[attr-defined]
        try:
            operation(storage)
        finally:
            storage.close()

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

    def _static(self, path: str) -> None:
        filename = {
            "/": "index.html",
            "/index.html": "index.html",
            "/app.js": "app.js",
            "/styles.css": "styles.css",
        }.get(path)
        if not filename:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = resources.files("skill_runtime_intelligence.web").joinpath(filename).read_bytes()
        content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'")
        self.end_headers()
        self.wfile.write(content)


def serve(database: Path, host: str = "127.0.0.1", port: int = 4317) -> None:
    server = ThreadingHTTPServer((host, port), PanoramaHandler)
    server.database_path = database.expanduser().resolve()  # type: ignore[attr-defined]
    print(f"Skill Runtime Intelligence: http://{host}:{port}")
    print(f"Database: {server.database_path}")
    print("Local-only server. Press Ctrl-C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
