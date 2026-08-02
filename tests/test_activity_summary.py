import unittest

from skill_runtime_intelligence.activity_summary import build_activity_summary


def event(event_id, event_type, stage, *, path="", call_id="", tool_name=""):
    payload = {}
    if path:
        payload["path"] = path
    if call_id:
        payload["call_id"] = call_id
    if tool_name:
        payload["tool_name"] = tool_name
    return {
        "event_id": event_id,
        "event_type": event_type,
        "stage": stage,
        "occurred_at": f"2026-07-31T00:00:0{event_id[-1]}Z",
        "status": "observed",
        "evidence_grade": "observed",
        "basis": "fixture source record",
        "summary": event_type,
        "payload": payload,
    }


class ActivitySummaryTests(unittest.TestCase):
    def test_observed_activation_and_resource_path_remain_concrete(self):
        run = {
            "cwd": "/workspace",
            "activation_mode": "explicit_tool",
            "events": [
                event("event-1", "skill.activated", "activation"),
                event(
                    "event-2",
                    "resource.read",
                    "resources",
                    path="/workspace/references/policy.md",
                ),
            ],
        }
        summary = build_activity_summary(run)
        entries = {entry["stage"]: entry for entry in summary["entries"]}

        self.assertEqual(entries["activation"]["status"], "observed")
        self.assertIn("explicit tool", entries["activation"]["headline"])
        self.assertEqual(
            entries["resources"]["objects"][0]["label"],
            "references/policy.md",
        )
        self.assertEqual(
            entries["resources"]["objects"][0]["location"],
            "workspace",
        )

    def test_pairs_tool_lifecycle_events_into_calls(self):
        run = {
            "cwd": "/workspace",
            "activation_mode": "unknown",
            "events": [
                event(
                    "event-1",
                    "tool.started",
                    "execution",
                    call_id="call-1",
                    tool_name="exec_command",
                ),
                event(
                    "event-2",
                    "tool.completed",
                    "execution",
                    call_id="call-1",
                    tool_name="exec_command",
                ),
            ],
        }

        result = build_activity_summary(run)
        execution = next(
            item for item in result["entries"] if item["stage"] == "execution"
        )

        self.assertEqual(execution["headline"], "1 tool calls · 2 lifecycle events")
        self.assertEqual(execution["objects"][0]["call_count"], 1)
        self.assertEqual(execution["objects"][0]["completed_count"], 1)
        self.assertEqual(execution["causal_scope"], "none")

    def test_groups_path_aliases_and_temporary_lifecycle(self):
        run = {
            "cwd": "/workspace",
            "events": [
                event(
                    "event-1",
                    "file.created",
                    "artifacts",
                    path="/tmp/sri-canary/hooks.json",
                ),
                {
                    **event(
                        "event-2",
                        "file.created",
                        "artifacts",
                        path="/private/tmp/sri-canary/hooks.json",
                    ),
                    "evidence_grade": "derived",
                },
                event(
                    "event-3",
                    "file.deleted",
                    "artifacts",
                    path="/tmp/sri-canary/hooks.json",
                ),
            ],
        }

        result = build_activity_summary(run)
        artifacts = next(
            item for item in result["entries"] if item["stage"] == "artifacts"
        )

        self.assertEqual(len(artifacts["objects"]), 1)
        self.assertEqual(
            artifacts["objects"][0]["label"], "tmp/sri-canary/hooks.json"
        )
        self.assertEqual(
            artifacts["objects"][0]["path_hint"],
            "/tmp/sri-canary/hooks.json",
        )
        self.assertEqual(
            artifacts["objects"][0]["final_state"], "temporary · removed"
        )
        self.assertEqual(artifacts["objects"][0]["evidence_grade"], "derived")

    def test_relative_artifact_path_is_resolved_against_run_workspace(self):
        run = {
            "cwd": "/workspace/example-product",
            "events": [
                event(
                    "event-1",
                    "file.created",
                    "artifacts",
                    path="docs/releases/v0.3.0.md",
                )
            ],
        }

        result = build_activity_summary(run)
        artifacts = next(
            item for item in result["entries"] if item["stage"] == "artifacts"
        )

        self.assertEqual(
            artifacts["objects"][0]["label"], "docs/releases/v0.3.0.md"
        )
        self.assertEqual(artifacts["objects"][0]["location"], "workspace")

    def test_reported_outcome_is_not_upgraded_to_verification(self):
        run = {
            "events": [
                event("event-1", "outcome.reported", "outcome"),
                event("event-2", "turn.completed", "outcome"),
            ]
        }

        result = build_activity_summary(run)
        outcome = next(
            item for item in result["entries"] if item["stage"] == "outcome"
        )

        self.assertEqual(outcome["status"], "reported_not_verified")
        self.assertIn("not independent proof", outcome["limitation"])
        final_response = next(
            item for item in outcome["objects"] if item["label"] == "Final response"
        )
        progress = next(
            item for item in outcome["objects"] if item["label"] == "Progress updates"
        )
        self.assertEqual(final_response["count"], 1)
        self.assertEqual(final_response["content"], "outcome.reported")
        self.assertEqual(final_response["content_scope"], "redacted normalized excerpt")
        self.assertEqual(progress["count"], 0)


if __name__ == "__main__":
    unittest.main()
