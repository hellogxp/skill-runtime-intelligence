import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.causal_scope_contract_benchmark import (
    run_benchmark,
)


class CausalScopeContractBenchmarkTests(unittest.TestCase):
    def test_current_single_run_findings_deny_effect_claims(self):
        report = run_benchmark(
            Path("experiments/runtime_diagnostics/cases.jsonl")
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(
            report["metrics"]["single_run_effect_claims_allowed"], 0
        )
        self.assertEqual(
            report["metrics"]["single_run_findings_with_none_scope"],
            report["metrics"]["finding_count"],
        )


if __name__ == "__main__":
    unittest.main()
