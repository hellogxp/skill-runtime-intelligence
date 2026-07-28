import json
import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.adapters.observability import ObservabilityAdapter
from skill_runtime_intelligence.discovery import parse_skill


class CodexAdapterTests(unittest.TestCase):
    def test_reconstructs_exact_skill_path_and_tool_relationship(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            skill_dir = root / "skills" / "pdf"
            skill_dir.mkdir(parents=True)
            skill_file = skill_dir / "SKILL.md"
            skill_file.write_text(
                "---\nname: pdf\ndescription: Inspect PDFs\n---\nInstructions.\n",
                encoding="utf-8",
            )
            session_file = root / "session.jsonl"
            records = [
                {
                    "timestamp": "2026-07-28T01:00:00Z",
                    "type": "session_meta",
                    "payload": {
                        "id": "session-1",
                        "cwd": str(root),
                        "cli_version": "0.1",
                    },
                },
                {
                    "timestamp": "2026-07-28T01:00:01Z",
                    "type": "event_msg",
                    "payload": {"type": "task_started", "turn_id": "turn-1"},
                },
                {
                    "timestamp": "2026-07-28T01:00:02Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "user_message",
                        "message": "Inspect with github_pat_" + ("x" * 48),
                    },
                },
                {
                    "timestamp": "2026-07-28T01:00:03Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call",
                        "name": "exec_command",
                        "call_id": "call-1",
                        "input": {"cmd": f"sed -n '1,80p' {skill_file}"},
                    },
                },
                {
                    "timestamp": "2026-07-28T01:00:04Z",
                    "type": "response_item",
                    "payload": {
                        "type": "function_call_output",
                        "call_id": "call-1",
                        "output": "instructions",
                    },
                },
                {
                    "timestamp": "2026-07-28T01:00:05Z",
                    "type": "event_msg",
                    "payload": {
                        "type": "task_complete",
                        "turn_id": "turn-1",
                        "duration_ms": 4000,
                    },
                },
            ]
            session_file.write_text(
                "".join(json.dumps(record) + "\n" for record in records),
                encoding="utf-8",
            )

            skill = parse_skill(skill_file)
            session, raw, events, skill_runs = CodexAdapter(root).parse(
                session_file, [skill]
            )

            self.assertEqual(session["status"], "completed")
            self.assertEqual(session["duration_ms"], 4000)
            self.assertEqual(len(raw), len(records))
            persisted_view = json.dumps([raw, events], ensure_ascii=False)
            self.assertNotIn("github_pat_", persisted_view)
            self.assertEqual(len(skill_runs), 1)
            loaded = [event for event in events if event["event_type"] == "instruction.loaded"]
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["evidence_grade"], "observed")
            completed = [event for event in events if event["event_type"] == "tool.completed"]
            self.assertEqual(len(completed), 1)
            self.assertTrue(completed[0]["parent_event_id"])
            self.assertEqual(loaded[0]["skill_run_id"], skill_runs[0]["skill_run_id"])
            attributed_tools = [
                event
                for event in events
                if event["event_type"] == "tool.completed"
                and event.get("skill_run_id")
            ]
            self.assertEqual(len(attributed_tools), 1)

    def test_imports_otel_skill_attribute_and_inherits_scope(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "otel.json"
            source.write_text(
                json.dumps(
                    {
                        "resourceSpans": [
                            {
                                "resource": {"attributes": []},
                                "scopeSpans": [
                                    {
                                        "spans": [
                                            {
                                                "traceId": "trace-1",
                                                "spanId": "span-root",
                                                "name": "pdf runtime",
                                                "startTimeUnixNano": "1000000000",
                                                "endTimeUnixNano": "3000000000",
                                                "attributes": [
                                                    {
                                                        "key": "skill.runtime.name",
                                                        "value": {"stringValue": "pdf"},
                                                    }
                                                ],
                                            },
                                            {
                                                "traceId": "trace-1",
                                                "spanId": "span-tool",
                                                "parentSpanId": "span-root",
                                                "name": "render",
                                                "startTimeUnixNano": "1500000000",
                                                "endTimeUnixNano": "2500000000",
                                                "attributes": [
                                                    {
                                                        "key": "openinference.span.kind",
                                                        "value": {"stringValue": "tool"},
                                                    }
                                                ],
                                            },
                                        ]
                                    }
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            skills, bundles, profile = ObservabilityAdapter(source).parse()

            self.assertEqual(profile, "otel")
            self.assertEqual([skill.name for skill in skills], ["pdf"])
            self.assertEqual(len(bundles), 1)
            _, _, events, runs = bundles[0]
            self.assertEqual(len(runs), 1)
            self.assertTrue(
                any(event["event_type"] == "skill.activated" for event in events)
            )
            inherited = [
                event
                for event in events
                if event["event_type"] == "tool.started"
            ]
            self.assertEqual(len(inherited), 1)
            self.assertEqual(inherited[0]["skill_run_id"], runs[0]["skill_run_id"])


if __name__ == "__main__":
    unittest.main()
