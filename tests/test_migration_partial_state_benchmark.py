import unittest

from experiments.product_lifecycle.migration_partial_state_benchmark import (
    run_benchmark,
)


class MigrationPartialStateBenchmarkTests(unittest.TestCase):
    def test_all_additive_prefix_states_recover(self):
        report = run_benchmark(trials=1)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 6)
        self.assertEqual(report["metrics"]["passed"], 6)
        self.assertEqual(report["metrics"]["failed"], 0)
        self.assertTrue(report["metrics"]["legacy_unknown_preserved"])
        self.assertTrue(report["metrics"]["idempotent_second_open"])


if __name__ == "__main__":
    unittest.main()
