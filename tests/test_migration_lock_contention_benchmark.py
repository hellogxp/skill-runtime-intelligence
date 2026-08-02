import unittest

from experiments.product_lifecycle.migration_lock_contention_benchmark import (
    run_benchmark,
)


class MigrationLockContentionBenchmarkTests(unittest.TestCase):
    def test_transient_lock_recovers_within_busy_timeout(self):
        report = run_benchmark(
            within_budget_holds=(0.01,),
            repetitions=1,
            over_budget_hold=None,
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 1)
        self.assertEqual(
            report["metrics"]["within_budget_initial_successes"],
            1,
        )
        self.assertEqual(
            report["metrics"]["clean_recovery_successes"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
