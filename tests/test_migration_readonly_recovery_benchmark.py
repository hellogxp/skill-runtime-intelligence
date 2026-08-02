import unittest

from experiments.product_lifecycle.migration_readonly_recovery_benchmark import (
    run_benchmark,
)


class MigrationReadonlyRecoveryBenchmarkTests(unittest.TestCase):
    def test_readonly_failure_is_non_destructive_and_recoverable(self):
        report = run_benchmark(trials=1)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["initial_readonly_failures"], 1)
        self.assertEqual(
            report["metrics"]["failed_attempts_schema_unchanged"],
            1,
        )
        self.assertEqual(
            report["metrics"]["clean_recovery_successes"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
