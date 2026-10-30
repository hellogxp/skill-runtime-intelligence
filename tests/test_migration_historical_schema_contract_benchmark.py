import unittest

from experiments.product_lifecycle.migration_historical_schema_contract_benchmark import (
    missing_historical_snapshots,
    run_benchmark,
)


class MigrationHistoricalSchemaContractBenchmarkTests(unittest.TestCase):
    def test_three_repository_history_contracts_migrate(self):
        missing = missing_historical_snapshots()
        if missing:
            self.skipTest(
                "historical Git snapshots unavailable in this checkout: "
                + ", ".join(missing)
            )
        report = run_benchmark(trials=1)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 3)
        self.assertEqual(
            report["metrics"]["distinct_historical_schema_fingerprints"],
            3,
        )
        self.assertEqual(
            report["metrics"]["snapshots_without_time_provenance"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
