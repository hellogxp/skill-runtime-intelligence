import unittest

from experiments.real_corpus_audit.mixed_provenance_benchmark import (
    run_experiment,
)


class MixedProvenanceBenchmarkTests(unittest.TestCase):
    def test_preservation_passes_while_relationship_merge_is_absent(self):
        report = run_experiment(2)

        self.assertTrue(
            report["gates"]["official_hook_evidence_preservation"]["passed"]
        )
        self.assertTrue(
            report["gates"]["correlation_group_preservation"]["passed"]
        )
        self.assertFalse(
            report["gates"]["merged_cross_source_relationship_plane"]["passed"]
        )
        self.assertFalse(report["gate"]["passed"])
        self.assertTrue(report["privacy_audit"]["passed"])
        self.assertEqual(report["metrics"]["hook_evidence_preserved"], 2)
        self.assertEqual(report["metrics"]["correlation_group_preserved"], 2)
        self.assertEqual(
            report["metrics"]["cross_source_relationship_available"],
            0,
        )
        self.assertNotIn("shared-source-session", str(report))


if __name__ == "__main__":
    unittest.main()
