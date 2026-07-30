import tempfile
import threading
import unittest
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from skill_runtime_intelligence.discovery import parse_skill
from skill_runtime_intelligence.indexer import index_local
from skill_runtime_intelligence.storage import Storage


class StorageTests(unittest.TestCase):
    def test_timestamp_provenance_migration_preserves_unknown_legacy_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            connection = sqlite3.connect(database)
            connection.execute(
                """
                CREATE TABLE normalized_events (
                    event_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    turn_id TEXT,
                    skill_id TEXT,
                    parent_event_id TEXT,
                    occurred_at TEXT,
                    event_type TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    status TEXT NOT NULL,
                    evidence_grade TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    basis TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    source_locator TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                INSERT INTO normalized_events (
                    event_id, session_id, occurred_at, event_type, stage, status,
                    evidence_grade, confidence, basis, summary, source_locator,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "legacy-event",
                    "legacy-session",
                    "2026-07-28T00:00:00Z",
                    "session.started",
                    "request",
                    "observed",
                    "observed",
                    1.0,
                    "legacy fixture",
                    "Legacy event",
                    "legacy:1",
                    "{}",
                ),
            )
            connection.commit()
            connection.close()

            storage = Storage(database)
            try:
                row = storage.connection.execute(
                    """
                    SELECT timestamp_origin, ingested_at, clock_domain,
                           clock_uncertainty_ms, timestamp_precision
                    FROM normalized_events
                    WHERE event_id = 'legacy-event'
                    """
                ).fetchone()
                self.assertEqual(row["timestamp_origin"], "unknown")
                self.assertIsNone(row["ingested_at"])
                self.assertEqual(row["clock_domain"], "unknown")
                self.assertIsNone(row["clock_uncertainty_ms"])
                self.assertEqual(row["timestamp_precision"], "unknown")
            finally:
                storage.close()

    def test_concurrent_fresh_database_initialization_is_serialized(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            barrier = threading.Barrier(12)
            failures = []
            failures_lock = threading.Lock()

            def initialize():
                try:
                    barrier.wait(timeout=2)
                    storage = Storage(database)
                    storage.close()
                except Exception as exc:
                    with failures_lock:
                        failures.append(exc)

            workers = [
                threading.Thread(target=initialize, daemon=True)
                for _ in range(12)
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=8)
            self.assertFalse(failures)
            self.assertTrue(all(not worker.is_alive() for worker in workers))
            storage = Storage(database)
            try:
                self.assertEqual(storage.counts()["sessions"], 0)
            finally:
                storage.close()

    def test_empty_index_is_queryable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions"
            skills = root / "skills"
            sessions.mkdir()
            skills.mkdir()
            database = root / "panorama.db"

            result = index_local(database, sessions, [skills])
            self.assertEqual(result["failed"], 0)

            storage = Storage(database)
            try:
                self.assertEqual(storage.list_runs(), [])
                self.assertEqual(storage.list_skills(), [])
            finally:
                storage.close()

    def test_skill_run_is_primary_and_keeps_attribution_edges(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_dir = root / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo\ndescription: Demo runtime\n---\n",
                encoding="utf-8",
            )
            database = root / "panorama.db"
            storage = Storage(database)
            skill = parse_skill(skill_file)
            run_id = "skillrun-1"
            session = {
                "session_id": "session-1",
                "adapter": "codex",
                "adapter_version": "0.2.0",
                "source_path": str(root / "session.jsonl"),
                "source_format_version": "fixture",
                "title": "Demo",
                "cwd": str(root),
                "model": "",
                "agent_version": "",
                "started_at": "2026-07-28T00:00:00Z",
                "ended_at": "2026-07-28T00:00:02Z",
                "duration_ms": 2000,
                "status": "completed",
                "completeness": "complete",
                "event_count": 1,
            }
            event = {
                "event_id": "event-1",
                "session_id": "session-1",
                "turn_id": "turn-1",
                "skill_id": skill.skill_id,
                "skill_run_id": run_id,
                "parent_event_id": None,
                "occurred_at": "2026-07-28T00:00:01Z",
                "event_type": "instruction.loaded",
                "stage": "instructions",
                "status": "observed",
                "evidence_grade": "observed",
                "confidence": 1.0,
                "basis": "fixture",
                "summary": "Instructions loaded",
                "source_locator": "fixture:1",
                "payload": {},
            }
            run = {
                "skill_run_id": run_id,
                "session_id": "session-1",
                "turn_id": "turn-1",
                "skill_id": skill.skill_id,
                "activation_mode": "unknown",
                "evidence_grade": "derived",
                "status": "completed",
                "started_at": "2026-07-28T00:00:01Z",
                "ended_at": "2026-07-28T00:00:02Z",
                "basis": "fixture",
            }
            try:
                storage.replace_skills([skill.to_dict()])
                storage.replace_session(session, [], [event], [run])
                listed = storage.list_skill_runs()
                self.assertEqual([item["skill_run_id"] for item in listed], [run_id])
                detail = storage.get_skill_run(run_id)
                self.assertEqual(detail["events"][0]["event_id"], "event-1")
                self.assertEqual(
                    detail["relationships"][0]["relationship_type"], "skill_scope"
                )
                self.assertEqual(
                    [finding["code"] for finding in detail["findings"]],
                    ["lifecycle_evidence_gap"],
                )
                self.assertEqual(detail["findings"][0]["stage"], "request")
            finally:
                storage.close()

    def test_inventory_records_resource_metadata_without_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_dir = root / "skills" / "demo"
            (skill_dir / "scripts").mkdir(parents=True)
            (skill_dir / "references").mkdir()
            (skill_dir / "assets").mkdir()
            (skill_dir / "scripts" / "run.py").write_text(
                "secret-script-body", encoding="utf-8"
            )
            (skill_dir / "references" / "guide.md").write_text(
                "reference-body", encoding="utf-8"
            )
            (skill_dir / "assets" / "template.bin").write_bytes(b"\x00\x01")
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\n"
                "name: demo\n"
                "description: Demo runtime\n"
                "version: 2.1.0\n"
                "compatibility: codex, claude-code\n"
                "---\n",
                encoding="utf-8",
            )
            skill = parse_skill(skill_file)
            storage = Storage(root / "panorama.db")
            try:
                storage.replace_skills([skill.to_dict()])
                inventory = storage.list_skills()[0]
                self.assertEqual(inventory["version"], "2.1.0")
                self.assertEqual(inventory["resource_counts"]["script"], 1)
                self.assertEqual(inventory["resource_counts"]["reference"], 1)
                self.assertEqual(inventory["resource_counts"]["asset"], 1)
                self.assertNotIn(
                    "secret-script-body", str(inventory["resources"])
                )
            finally:
                storage.close()

    def test_delete_skill_run_removes_only_indexed_data(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.jsonl"
            source.write_text("authoritative source", encoding="utf-8")
            database = root / "panorama.db"
            storage = Storage(database)
            skill_dir = root / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo\ndescription: demo\n---\n", encoding="utf-8"
            )
            skill = parse_skill(skill_file)
            session = {
                "session_id": "delete-session",
                "adapter": "codex",
                "adapter_version": "0.2.0",
                "source_path": str(source),
                "source_format_version": "fixture",
                "title": "Delete fixture",
                "cwd": str(root),
                "model": "",
                "agent_version": "",
                "started_at": "2026-07-28T00:00:00Z",
                "ended_at": None,
                "duration_ms": None,
                "status": "incomplete",
                "completeness": "partial",
                "event_count": 0,
            }
            run = {
                "skill_run_id": "delete-run",
                "session_id": "delete-session",
                "turn_id": "turn-1",
                "skill_id": skill.skill_id,
                "activation_mode": "explicit_tool",
                "evidence_grade": "observed",
                "status": "incomplete",
                "started_at": "2026-07-28T00:00:00Z",
                "ended_at": None,
                "basis": "fixture",
            }
            try:
                storage.replace_skills([skill.to_dict()])
                storage.replace_session(session, [], [], [run])
                result = storage.delete_skill_run("delete-run")
                self.assertTrue(result["session_deleted"])
                self.assertFalse(result["source_transcript_deleted"])
                self.assertEqual(storage.counts()["skill_runs"], 0)
                self.assertEqual(source.read_text(encoding="utf-8"), "authoritative source")
            finally:
                storage.close()

    def test_definition_comparison_reports_static_changes_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            definitions = []
            for folder, version, resource in (
                ("left", "1.0.0", "old.py"),
                ("right", "2.0.0", "new.py"),
            ):
                skill_dir = root / folder / "demo"
                (skill_dir / "scripts").mkdir(parents=True)
                (skill_dir / "scripts" / resource).write_text(
                    "print('metadata only')", encoding="utf-8"
                )
                skill_file = skill_dir / "SKILL.md"
                skill_file.write_text(
                    "---\n"
                    "name: demo\n"
                    f"description: Demo version {version}\n"
                    f"version: {version}\n"
                    "---\n",
                    encoding="utf-8",
                )
                definitions.append(parse_skill(skill_file))
            storage = Storage(root / "panorama.db")
            try:
                storage.replace_skills(
                    [definition.to_dict() for definition in definitions]
                )
                result = storage.compare_skill_definitions(
                    definitions[0].skill_id,
                    definitions[1].skill_id,
                )
                self.assertTrue(result["same_name"])
                self.assertFalse(result["same_digest"])
                self.assertIn("version", result["changed_fields"])
                self.assertEqual(
                    result["resources_added"][0]["path"],
                    "scripts/new.py",
                )
                self.assertEqual(result["evidence_grade"], "observed")
                self.assertNotIn("metadata only", str(result))
            finally:
                storage.close()

    def test_retention_removes_index_only_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "old-session.jsonl"
            source.write_text("authoritative source", encoding="utf-8")
            skill_dir = root / "skills" / "demo"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: demo\ndescription: demo\n---\n",
                encoding="utf-8",
            )
            skill = parse_skill(skill_file)
            storage = Storage(root / "panorama.db")
            try:
                storage.replace_skills([skill.to_dict()])
                storage.replace_session(
                    {
                        "session_id": "old-session",
                        "adapter": "codex",
                        "adapter_version": "0.2.0",
                        "source_path": str(source),
                        "source_format_version": "fixture",
                        "title": "Old",
                        "cwd": str(root),
                        "model": "",
                        "agent_version": "",
                        "started_at": "2026-01-01T00:00:00+00:00",
                        "ended_at": "2026-01-01T00:01:00+00:00",
                        "duration_ms": 60000,
                        "status": "completed",
                        "completeness": "complete",
                        "event_count": 0,
                    },
                    [],
                    [],
                    [],
                )
                result = storage.purge_expired(
                    30,
                    now=datetime(2026, 7, 29, tzinfo=timezone.utc),
                )
                self.assertEqual(result["sessions_deleted"], 1)
                self.assertFalse(result["source_transcripts_deleted"])
                self.assertEqual(storage.counts()["sessions"], 0)
                self.assertEqual(
                    source.read_text(encoding="utf-8"),
                    "authoritative source",
                )
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
