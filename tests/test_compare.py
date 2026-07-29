import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.storage import Storage


def _event(event_id, session_id, event_type, skill, occurred_at):
    return {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": occurred_at,
        "session_id": session_id,
        "turn_id": "turn-1",
        "skill": {"name": skill},
        "source": {
            "adapter": "codex",
            "adapter_version": "0.1.0",
            "collection_mode": "official_hook",
            "source_event_id": event_id,
        },
        "evidence": {"grade": "observed", "confidence": 1.0, "basis": "test"},
    }


class CompareTests(unittest.TestCase):
    def test_compare_aligns_stages_without_inventing_causal_difference(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            storage = Storage(database)
            try:
                left = normalize_collector_payload(
                    _event(
                        "left-activation",
                        "left-session",
                        "skill.activated",
                        "pdf",
                        "2026-07-29T06:00:00Z",
                    )
                )
                right = normalize_collector_payload(
                    [
                        _event(
                            "right-activation",
                            "right-session",
                            "skill.activated",
                            "pdf",
                            "2026-07-29T06:01:00Z",
                        ),
                        _event(
                            "right-tool",
                            "right-session",
                            "tool.started",
                            "pdf",
                            "2026-07-29T06:01:01Z",
                        ),
                    ]
                )
                storage.append_collector_events(left)
                storage.append_collector_events(right)
                left_id = left[0]["event"]["skill_run_id"]
                right_id = right[0]["event"]["skill_run_id"]
                comparison = storage.compare_skill_runs(left_id, right_id)
            finally:
                storage.close()

            self.assertIsNotNone(comparison)
            self.assertTrue(comparison["same_skill_name"])
            self.assertEqual(comparison["first_changed_stage"], "execution")
            activation = next(
                stage for stage in comparison["stages"]
                if stage["stage"] == "activation"
            )
            self.assertEqual(activation["comparability"], "comparable")
            self.assertFalse(activation["changed"])
            discovery = next(
                stage for stage in comparison["stages"]
                if stage["stage"] == "discovery"
            )
            self.assertEqual(discovery["comparability"], "unsupported")
            self.assertIsNone(discovery["changed"])


if __name__ == "__main__":
    unittest.main()
