import unittest

from experiments.diagnostic_usefulness.summarize_cross_model_guard_studies import (
    _percentile,
)


class CrossModelGuardSummaryTests(unittest.TestCase):
    def test_percentile_interpolates_sorted_values(self):
        self.assertEqual(_percentile([3.0, 1.0, 2.0], 0.5), 2.0)
        self.assertAlmostEqual(
            _percentile([0.0, 10.0], 0.95), 9.5
        )

    def test_empty_percentile_is_zero(self):
        self.assertEqual(_percentile([], 0.95), 0.0)


if __name__ == "__main__":
    unittest.main()
