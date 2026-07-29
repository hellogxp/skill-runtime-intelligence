import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.otlp_exporter import (
    export_otlp_once,
    normalize_otlp_endpoint,
)
from skill_runtime_intelligence.storage import Storage


class _CaptureHandler(BaseHTTPRequestHandler):
    requests = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        self.__class__.requests.append(
            {
                "path": self.path,
                "headers": dict(self.headers),
                "body": json.loads(self.rfile.read(length)),
            }
        )
        self.send_response(200)
        self.end_headers()

    def log_message(self, fmt, *args):
        return


class OtlpExporterTests(unittest.TestCase):
    def _database(self, root: Path) -> Path:
        database = root / "panorama.db"
        bundle = normalize_collector_payload(
            {
                "event_id": "evt-otlp",
                "event_type": "skill.activated",
                "occurred_at": "2026-07-29T06:00:00Z",
                "session_id": "otlp-session",
                "turn_id": "turn-1",
                "skill": {"name": "pdf"},
                "source": {
                    "adapter": "codex",
                    "adapter_version": "0.1.0",
                    "collection_mode": "official_hook",
                    "source_event_id": "source-otlp",
                },
                "evidence": {
                    "grade": "observed",
                    "confidence": 1.0,
                    "basis": "test hook",
                },
            }
        )
        storage = Storage(database)
        try:
            storage.append_collector_events(bundle)
        finally:
            storage.close()
        return database

    def test_export_is_opt_in_idempotent_and_skill_specific(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self._database(root)
            _CaptureHandler.requests = []
            server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            endpoint = f"http://127.0.0.1:{server.server_port}"
            try:
                first = export_otlp_once(
                    database,
                    endpoint,
                    headers={"X-Test-Tenant": "tenant-1"},
                )
                second = export_otlp_once(database, endpoint)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

            self.assertEqual(first["exported"], 1)
            self.assertEqual(second["exported"], 0)
            self.assertEqual(len(_CaptureHandler.requests), 1)
            request = _CaptureHandler.requests[0]
            self.assertEqual(request["path"], "/v1/traces")
            self.assertEqual(request["headers"]["X-Test-Tenant"], "tenant-1")
            span = request["body"]["resourceSpans"][0]["scopeSpans"][0]["spans"][0]
            attributes = {
                item["key"]: next(iter(item["value"].values()))
                for item in span["attributes"]
            }
            self.assertEqual(attributes["skill.runtime.name"], "pdf")
            self.assertEqual(
                attributes["skill.runtime.evidence.grade"], "observed"
            )

    def test_failed_endpoint_does_not_advance_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = self._database(root)
            failed = export_otlp_once(
                database,
                "http://127.0.0.1:1",
                timeout_seconds=0.02,
            )
            self.assertTrue(failed["pending"])
            self.assertTrue(failed["last_error"])

            _CaptureHandler.requests = []
            server = ThreadingHTTPServer(("127.0.0.1", 0), _CaptureHandler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                recovered = export_otlp_once(
                    database,
                    f"http://127.0.0.1:{server.server_port}",
                )
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)
            self.assertEqual(recovered["exported"], 1)

    def test_endpoint_validation(self):
        self.assertEqual(
            normalize_otlp_endpoint("https://example.test"),
            "https://example.test/v1/traces",
        )
        self.assertEqual(
            normalize_otlp_endpoint("https://example.test/custom/v1/traces"),
            "https://example.test/custom/v1/traces",
        )
        with self.assertRaises(ValueError):
            normalize_otlp_endpoint("file:///tmp/traces")


if __name__ == "__main__":
    unittest.main()
