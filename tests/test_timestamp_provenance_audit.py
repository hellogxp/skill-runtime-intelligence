import unittest

from experiments.cross_agent.timestamp_provenance_audit import run_audit


class TimestampProvenanceAuditTests(unittest.TestCase):
    def test_audit_distinguishes_timestamp_presence_from_provenance(self):
        report = run_audit()

        self.assertTrue(report["gate"]["passed"])
        self.assertTrue(report["privacy_audit"]["passed"])
        self.assertEqual(
            report["metrics"]["available_capability_count"],
            7,
        )
        self.assertFalse(
            report["metrics"]["cross_agent_absolute_time_ready"]
        )
        behavior = report["metrics"]["hook_behavior"]
        self.assertEqual(
            behavior["explicit_source_timestamp_preserved"],
            behavior["agent_profiles"],
        )
        self.assertEqual(
            behavior["missing_timestamp_fallback_generated"],
            behavior["agent_profiles"],
        )
        self.assertEqual(
            behavior["fallback_provenance_labeled"],
            behavior["agent_profiles"],
        )
        self.assertEqual(behavior["normalized_event_count"], 8)
        self.assertEqual(behavior["persisted_event_count"], 8)
        self.assertEqual(behavior["ingestion_timestamp_labeled"], 8)
        self.assertEqual(behavior["clock_domain_labeled"], 8)
        self.assertEqual(behavior["timestamp_precision_labeled"], 8)
        self.assertEqual(behavior["clock_uncertainty_labeled"], 0)


if __name__ == "__main__":
    unittest.main()
