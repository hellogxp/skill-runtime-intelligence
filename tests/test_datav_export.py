import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import urlopen

from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.datav import build_datav_datasets
from skill_runtime_intelligence.server import create_server
from skill_runtime_intelligence.storage import Storage


def _event(event_id: str, event_type: str, occurred_at: str) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "session_id": "datav-session",
        "turn_id": "datav-turn",
        "run_token": "datav-run",
        "summary": "sensitive-looking summary must not be exported",
        "context": {
            "title": "private task title",
            "cwd": "/private/customer/project",
            "model": "example-model",
            "agent_version": "1.0",
        },
        "skill": {
            "name": "data-development",
            "description": "Develop data jobs",
            "source_path": "/private/customer/skills/data-development/SKILL.md",
            "source_kind": "project",
        },
        "source": {
            "adapter": "codex",
            "adapter_version": "0.1.0",
            "collection_mode": "official_hook",
            "source_event_id": event_id,
            "record_locator": "private:record:1",
        },
        "evidence": {
            "grade": "observed",
            "confidence": 1.0,
            "basis": "test event",
        },
        "payload": {"prompt": "do not export this", "token": "secret"},
        "activation_mode": "explicit_tool",
    }


class DataVExportTests(unittest.TestCase):
    def _database(self, root: Path) -> Path:
        database = root / "panorama.db"
        storage = Storage(database)
        try:
            storage.append_collector_events(
                normalize_collector_payload(
                    [
                        _event("datav-1", "skill.activated", "2026-08-03T08:00:00Z"),
                        _event("datav-2", "tool.failed", "2026-08-03T08:00:01Z"),
                    ]
                )
            )
        finally:
            storage.close()
        return database

    def test_datasets_are_flat_evidence_labeled_and_privacy_minimized(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._database(Path(directory))
            storage = Storage(database)
            try:
                datasets = build_datav_datasets(storage)
            finally:
                storage.close()

            self.assertEqual(datasets["manifest"]["version"], "sri-datav-v1")
            self.assertTrue(all(isinstance(datasets[name], list) for name in (
                "summary", "boundaries", "skills", "runs"
            )))
            self.assertEqual(datasets["runs"][0]["skill_name"], "data-development")
            self.assertEqual(datasets["runs"][0]["explicit_error_count"], 1)
            encoded = json.dumps(datasets, ensure_ascii=False)
            for forbidden in (
                "/private/customer",
                "private task title",
                "do not export this",
                "sensitive-looking summary",
                "secret",
            ):
                self.assertNotIn(forbidden, encoded)

    def test_http_endpoints_return_manifest_and_chart_arrays(self):
        with tempfile.TemporaryDirectory() as directory:
            database = self._database(Path(directory))
            server = create_server(database, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urlopen(f"{base}/api/datav", timeout=3) as response:
                    manifest = json.loads(response.read())
                self.assertEqual(manifest["version"], "sri-datav-v1")
                for dataset in ("summary", "boundaries", "skills", "runs"):
                    with urlopen(f"{base}/api/datav/{dataset}", timeout=3) as response:
                        value = json.loads(response.read())
                    self.assertIsInstance(value, list)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
