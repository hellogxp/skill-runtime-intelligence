import unittest

from experiments.real_corpus_audit.codex_watch_epoch_benchmark import (
    run_experiment,
)


class CodexWatchEpochBenchmarkTests(unittest.TestCase):
    def test_real_adapter_watch_path_and_deletion_boundary_pass(self):
        report = run_experiment(1)

        self.assertTrue(
            report["gates"]["new_and_appended_source_watch_path"]["passed"]
        )
        self.assertTrue(
            report["gates"]["deleted_source_collection_boundary"]["passed"]
        )
        self.assertTrue(report["gate"]["passed"])
        self.assertTrue(report["privacy_audit"]["passed"])
        self.assertEqual(report["metrics"]["initial_ingestion"], 1)
        self.assertEqual(report["metrics"]["append_reindexed"], 1)
        self.assertEqual(
            report["metrics"]["session_retained_after_source_deletion"],
            1,
        )
        self.assertEqual(report["metrics"]["deletion_count_recorded"], 1)
        self.assertNotIn("controlled-session", str(report))


if __name__ == "__main__":
    unittest.main()
