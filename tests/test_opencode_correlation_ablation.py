import unittest

from experiments.live_agent.run_opencode_correlation_ablation import (
    _bootstrap_mean_ci,
    _schedule,
)


class OpenCodeCorrelationAblationTests(unittest.TestCase):
    def test_schedule_is_reproducible_balanced_and_blocked(self):
        first = _schedule(8, 20260731)
        self.assertEqual(first, _schedule(8, 20260731))
        self.assertEqual(len(first), 16)
        for block in range(1, 9):
            conditions = {
                row["condition"] for row in first if row["block"] == block
            }
            self.assertEqual(conditions, {"token_on", "token_off"})

    def test_bootstrap_interval_is_reproducible(self):
        first = _bootstrap_mean_ci([-2.0, -1.0, 1.0, 2.0], 7, draws=100)
        self.assertEqual(first, _bootstrap_mean_ci(
            [-2.0, -1.0, 1.0, 2.0], 7, draws=100
        ))
        self.assertLessEqual(first[0], first[1])


if __name__ == "__main__":
    unittest.main()
