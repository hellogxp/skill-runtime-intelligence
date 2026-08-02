import unittest

from experiments.live_agent.run_catalog_ablation_paired import (
    _bootstrap_mean_interval,
    _percentile,
)


class CatalogAblationPairedTests(unittest.TestCase):
    def test_percentile_interpolates_endpoints(self):
        self.assertEqual(1.0, _percentile([3.0, 1.0], 0.0))
        self.assertEqual(3.0, _percentile([3.0, 1.0], 1.0))
        self.assertEqual(2.0, _percentile([3.0, 1.0], 0.5))

    def test_bootstrap_is_seeded_and_contains_constant_mean(self):
        self.assertEqual(
            [5.0, 5.0],
            _bootstrap_mean_interval([5.0, 5.0, 5.0], seed=7),
        )


if __name__ == "__main__":
    unittest.main()
