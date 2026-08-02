import unittest

from experiments.cross_agent.alignment_clock_sensitivity import (
    run_experiment,
)


class AlignmentClockSensitivityTests(unittest.TestCase):
    def test_clock_policy_only_changes_absolute_time_mask(self):
        report = run_experiment(
            offsets=[0, 2, 7],
            tolerances=[0, 2, 10],
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["evaluations"], 9)
        self.assertEqual(report["metrics"]["invariant_failures"], 0)
        self.assertEqual(
            [
                row["absolute_time_accepted"]
                for row in report["metrics"]["acceptance_by_tolerance"]
            ],
            [1, 2, 3],
        )
        self.assertEqual(
            report["metrics"]["overall_comparability_changed_evaluations"],
            0,
        )
        self.assertEqual(
            report["metrics"]["causal_attribution_enabled_evaluations"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
