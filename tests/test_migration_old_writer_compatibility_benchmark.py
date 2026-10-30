import unittest

from experiments.product_lifecycle.migration_old_writer_compatibility_benchmark import (
    run_benchmark,
)


class MigrationOldWriterCompatibilityBenchmarkTests(unittest.TestCase):
    def test_old_writer_column_list_remains_compatible(self):
        report = run_benchmark(
            within_budget_holds=(),
            repetitions=1,
            over_budget_hold=None,
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 1)
        self.assertTrue(report["metrics"]["all_old_writes_preserved"])
        self.assertTrue(report["metrics"]["all_old_writes_remain_unknown"])


if __name__ == "__main__":
    unittest.main()
