import unittest

from experiments.product_lifecycle.host_identity_contract_benchmark import (
    run_benchmark,
)


class HostIdentityContractBenchmarkTests(unittest.TestCase):
    def test_small_contract_matrix_passes(self):
        report = run_benchmark(trials=1, workers=3)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["worker_initializations"], 3)
        self.assertEqual(report["metrics"]["passed_trials"], 1)


if __name__ == "__main__":
    unittest.main()
