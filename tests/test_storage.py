import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.discovery import parse_skill
from skill_runtime_intelligence.indexer import index_local
from skill_runtime_intelligence.storage import Storage


class StorageTests(unittest.TestCase):
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
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
