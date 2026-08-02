import unittest

from experiments.product_lifecycle.migration_kill_recovery_benchmark import (
    run_benchmark,
)


class MigrationKillRecoveryBenchmarkTests(unittest.TestCase):
    def test_all_committed_boundaries_recover_after_sigkill(self):
        report = run_benchmark(trials=1)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 6)
        self.assertEqual(
            report["metrics"]["workers_terminated_by_signal"],
            6,
        )
        self.assertEqual(report["metrics"]["passed"], 6)
        self.assertEqual(report["metrics"]["failed"], 0)


if __name__ == "__main__":
    unittest.main()
