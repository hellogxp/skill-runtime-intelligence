import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from skill_runtime_intelligence.collector import (
    CollectorValidationError,
    normalize_collector_payload,
)
from skill_runtime_intelligence.config import load_config
from skill_runtime_intelligence.discovery import parse_skill
from skill_runtime_intelligence.server import create_server
from skill_runtime_intelligence.storage import Storage


def fixture_event(event_id="evt-fixture"):
    return {
        "event_id": event_id,
        "event_type": "skill.activated",
        "occurred_at": "2026-07-29T05:00:00Z",
        "session_id": "native-session-1",
        "turn_id": "turn-1",
        "activation_mode": "explicit_tool",
        "skill": {
            "name": "pdf",
            "description": "Inspect PDF layouts",
            "source_path": "/tmp/skills/pdf/SKILL.md",
        },
        "source": {
            "adapter": "codex",
            "adapter_version": "0.3.0",
            "collection_mode": "official_hook",
            "source_event_id": "hook-event-1",
            "record_locator": "hook:hook-event-1",
        },
        "evidence": {
            "grade": "observed",
            "confidence": 1.0,
            "basis": "Official runtime hook",
        },
        "payload": {
            "tool_name": "Skill",
            "access_token": "should-never-be-persisted",
        },
    }


class CollectorTests(unittest.TestCase):
    def test_timestamp_fallback_is_labeled_and_uncertainty_is_bounded(self):
        event = fixture_event("evt-fallback")
        event.pop("occurred_at")
        normalized = normalize_collector_payload(event)[0]["event"]
        self.assertEqual(normalized["timestamp_origin"], "collector_fallback")
        self.assertTrue(normalized["occurred_at"].endswith("Z"))
        self.assertTrue(normalized["ingested_at"].endswith("Z"))

        invalid = fixture_event("evt-invalid-uncertainty")
        invalid["clock_uncertainty_ms"] = -1
        with self.assertRaises(CollectorValidationError):
            normalize_collector_payload(invalid)

    def test_live_event_is_redacted_idempotent_and_primary(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            storage = Storage(database)
            try:
                storage.replace_session(
                    {
                        "session_id": "native-session-1",
                        "adapter": "codex",
                        "adapter_version": "0.2.0",
                        "source_path": str(Path(directory) / "session.jsonl"),
                        "source_format_version": "jsonl",
                        "title": "Transcript fallback",
                        "cwd": directory,
                        "model": "",
                        "agent_version": "",
                        "started_at": "2026-07-29T04:59:00Z",
                        "ended_at": None,
                        "duration_ms": None,
                        "status": "incomplete",
                        "completeness": "partial",
                        "event_count": 0,
                    },
                    [],
                    [],
                    [],
                )
                bundles = normalize_collector_payload(fixture_event())
                first = storage.append_collector_events(bundles)
                revision = storage.revision()
                second = storage.append_collector_events(bundles)

                self.assertEqual(first, {"accepted": 1, "duplicates": 0})
                self.assertEqual(second, {"accepted": 0, "duplicates": 1})
                self.assertEqual(storage.revision(), revision)
                self.assertEqual(storage.counts()["normalized_events"], 1)

                sources = storage.list_sources()
                self.assertEqual(storage.counts()["sessions"], 2)
                self.assertEqual(
                    {source["role"] for source in sources}, {"fallback", "primary"}
                )
                source = next(
                    item for item in sources if item["collection_mode"] == "official_hook"
                )
                self.assertTrue(source["live"])
                correlation_keys = {
                    row[0]
                    for row in storage.connection.execute(
                        "SELECT correlation_key FROM sessions"
                    ).fetchall()
                }
                self.assertEqual(correlation_keys, {"codex:native-session-1"})

                skill_run = storage.list_skill_runs()[0]
                detail = storage.get_skill_run(skill_run["skill_run_id"])
                event = detail["events"][0]
                self.assertEqual(event["timestamp_origin"], "source")
                self.assertTrue(event["ingested_at"].endswith("Z"))
                self.assertEqual(event["clock_domain"], "unknown")
                self.assertIsNone(event["clock_uncertainty_ms"])
                self.assertEqual(event["timestamp_precision"], "unknown")
                persisted = json.dumps(detail, ensure_ascii=False)
                self.assertNotIn("should-never-be-persisted", persisted)
                self.assertIn("[REDACTED]", persisted)

                raw = storage.connection.execute(
                    "SELECT redacted_envelope_json FROM raw_source_records"
                ).fetchone()[0]
                self.assertNotIn("should-never-be-persisted", raw)
                self.assertIn("[REDACTED]", raw)
            finally:
                storage.close()

    def test_http_collector_accepts_event_and_rejects_unknown_type(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            server = create_server(database, "127.0.0.1", 0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                body = json.dumps(fixture_event("evt-http")).encode("utf-8")
                request = Request(
                    f"{base_url}/api/events",
                    data=body,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=3) as response:
                    result = json.loads(response.read())
                self.assertEqual(response.status, 202)
                self.assertEqual(result["accepted"], 1)
                self.assertGreater(result["revision"], 0)

                with urlopen(f"{base_url}/api/sources", timeout=3) as response:
                    sources = json.loads(response.read())["sources"]
                self.assertEqual(sources[0]["role"], "primary")

                with urlopen(f"{base_url}/locale-packs.js", timeout=3) as response:
                    locale_packs = response.read().decode("utf-8")
                self.assertIn("SkillRuntimeLocalePacks", locale_packs)
                self.assertIn('"pt-BR"', locale_packs)

                with urlopen(f"{base_url}/favicon.svg", timeout=3) as response:
                    favicon = response.read().decode("utf-8")
                    content_type = response.headers["Content-Type"]
                self.assertIn("image/svg+xml", content_type)
                self.assertIn("<svg", favicon)

                invalid = fixture_event("evt-invalid")
                invalid["event_type"] = "model.secret_thought"
                request = Request(
                    f"{base_url}/api/events",
                    data=json.dumps(invalid).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with self.assertRaises(HTTPError) as caught:
                    urlopen(request, timeout=3)
                self.assertEqual(caught.exception.code, 400)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_settings_and_skill_compare_apis_use_server_local_config(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "panorama.db"
            config_path = root / "state" / "config.json"
            definitions = []
            for folder, version in (("left", "1.0.0"), ("right", "2.0.0")):
                skill_dir = root / folder / "demo"
                skill_dir.mkdir(parents=True)
                skill_file = skill_dir / "SKILL.md"
                skill_file.write_text(
                    "---\n"
                    "name: demo\n"
                    f"description: Demo {version}\n"
                    f"version: {version}\n"
                    "---\n",
                    encoding="utf-8",
                )
                definitions.append(parse_skill(skill_file))
            storage = Storage(database)
            try:
                storage.replace_skills(
                    [definition.to_dict() for definition in definitions]
                )
            finally:
                storage.close()
            server = create_server(
                database,
                "127.0.0.1",
                0,
                config_path=config_path,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                request = Request(
                    f"{base_url}/api/settings",
                    data=json.dumps(
                        {
                            "projects": [str(root / "project")],
                            "exclude_paths": [str(root / "private")],
                            "retention_days": 30,
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urlopen(request, timeout=3) as response:
                    saved = json.loads(response.read())
                self.assertEqual(saved["config_path"], str(config_path.resolve()))
                self.assertEqual(load_config(config_path)["retention_days"], 30)

                query = urlencode(
                    {
                        "left": definitions[0].skill_id,
                        "right": definitions[1].skill_id,
                    }
                )
                with urlopen(
                    f"{base_url}/api/skill-compare?{query}", timeout=3
                ) as response:
                    comparison = json.loads(response.read())
                self.assertEqual(comparison["evidence_grade"], "observed")
                self.assertIn("version", comparison["changed_fields"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
