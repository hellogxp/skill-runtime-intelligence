import json
import unittest

from experiments.cross_agent.coverage_readiness_audit import _aggregate
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)


def _record(
    adapter,
    index,
    *,
    digest="shared-skill",
    activated=True,
    verified=True,
    failed=True,
):
    event_types = {"tool.started", "tool.completed"}
    if activated:
        event_types.add("skill.activated")
    if verified:
        event_types.add("outcome.verified")
    return {
        "adapter": adapter,
        "session_key": f"{adapter}-session-{index // 2}",
        "skill_digest": digest,
        "event_types": event_types,
        "event_stages": {"activation", "execution", "outcome"},
        "explicit_failed_event": failed,
    }


class CrossAgentCoverageReadinessTests(unittest.TestCase):
    def test_balanced_presence_and_descriptive_gates_pass(self):
        records = [
            _record(adapter, index)
            for adapter in ("qoder", "opencode")
            for index in range(5)
        ]
        metrics, readiness = _aggregate(records)

        self.assertEqual(metrics["adapter_count"], 2)
        self.assertEqual(metrics["run_count_imbalance_ratio"], 1.0)
        self.assertEqual(metrics["shared_skill_digest_count"], 1)
        self.assertTrue(readiness["presence"]["multi_adapter_presence"])
        self.assertTrue(
            readiness["descriptive"]["cross_agent_descriptive_ready"]
        )
        self.assertFalse(
            readiness["confirmatory"]["cross_agent_confirmatory_ready"]
        )

    def test_sparse_minority_adapter_fails_descriptive_gate(self):
        records = [
            *[_record("codex", index) for index in range(20)],
            _record("qoder", 0),
            _record("opencode", 0),
        ]
        metrics, readiness = _aggregate(records)

        self.assertEqual(metrics["adapter_count"], 3)
        self.assertEqual(metrics["run_count_imbalance_ratio"], 20.0)
        self.assertTrue(readiness["presence"]["multi_adapter_presence"])
        self.assertFalse(
            readiness["descriptive"]["cross_agent_descriptive_ready"]
        )
        self.assertFalse(
            readiness["confirmatory"]["cross_agent_confirmatory_ready"]
        )

    def test_aggregate_contains_no_row_level_identifiers(self):
        records = [_record("codex", 0), _record("qoder", 0)]
        metrics, readiness = _aggregate(records)
        serialized = json.dumps(
            {"metrics": metrics, "readiness": readiness},
            sort_keys=True,
        )

        self.assertNotIn("session-0", serialized)
        self.assertNotIn("shared-skill", serialized)
        self.assertFalse(
            _contains_forbidden_row_data(
                {"metrics": metrics, "readiness": readiness}
            )
        )


if __name__ == "__main__":
    unittest.main()
