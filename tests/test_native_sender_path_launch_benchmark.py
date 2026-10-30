import unittest

from experiments.product_lifecycle.native_sender_path_launch_benchmark import (
    CELLS,
    balanced_order,
    summarize,
)


class NativeSenderPathLaunchBenchmarkTests(unittest.TestCase):
    def test_balanced_order_covers_each_position_equally(self):
        positions = {cell: [0, 0, 0, 0] for cell in CELLS}
        for block in range(8):
            order = balanced_order(block)
            self.assertEqual(set(order), set(CELLS))
            for position, cell in enumerate(order):
                positions[cell][position] += 1

        self.assertTrue(
            all(counts == [2, 2, 2, 2] for counts in positions.values())
        )

    def test_summary_uses_interpolated_p95(self):
        result = summarize([1.0, 2.0, 3.0, 4.0])

        self.assertEqual(result["count"], 4)
        self.assertEqual(result["p50_ms"], 2.5)
        self.assertAlmostEqual(result["p95_ms"], 3.85)


if __name__ == "__main__":
    unittest.main()
