import unittest

from experiments.product_lifecycle.native_sender_launch_factor_benchmark import (
    CELLS,
    balanced_order,
    factor_deltas,
)


class NativeSenderLaunchFactorBenchmarkTests(unittest.TestCase):
    def test_eight_blocks_balance_each_cell_position(self):
        positions = {cell: [0] * 8 for cell in CELLS}
        for block in range(8):
            order = balanced_order(block)
            self.assertEqual(set(order), set(CELLS))
            for position, cell in enumerate(order):
                positions[cell][position] += 1

        self.assertTrue(
            all(counts == [1] * 8 for counts in positions.values())
        )

    def test_four_cell_manifest_order_balances_in_four_blocks(self):
        cells = tuple(cell for cell in CELLS if cell[1] == "preserved")
        positions = {cell: [0] * 4 for cell in cells}
        for block in range(4):
            for position, cell in enumerate(balanced_order(block, cells)):
                positions[cell][position] += 1

        self.assertTrue(
            all(counts == [1] * 4 for counts in positions.values())
        )

    def test_factor_deltas_average_over_other_factors(self):
        rows = []
        for placement, provenance, signature in CELLS:
            rows.append(
                {
                    "block": 0,
                    "placement": placement,
                    "provenance": provenance,
                    "signature": signature,
                    "wall_ms": (
                        (10 if placement == "atomic_replace" else 0)
                        + (20 if provenance == "removed" else 0)
                        + (30 if signature == "adhoc_resigned" else 0)
                    ),
                }
            )

        result = factor_deltas(rows)

        self.assertEqual(result["placement"]["delta_ms"]["p50_ms"], 10)
        self.assertEqual(result["provenance"]["delta_ms"]["p50_ms"], 20)
        self.assertEqual(result["signature"]["delta_ms"]["p50_ms"], 30)


if __name__ == "__main__":
    unittest.main()
