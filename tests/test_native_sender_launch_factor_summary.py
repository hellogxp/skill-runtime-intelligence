import unittest

from experiments.product_lifecycle.summarize_native_launch_factor_reports import (
    summarize_reports,
)


def _report(delta):
    rows = []
    cell_summaries = {}
    for placement in ("direct_copy", "atomic_replace"):
        for signature in ("original_linker", "adhoc_resigned"):
            key = f"{placement}:preserved:{signature}"
            wall_ms = 10 + (
                delta if signature == "adhoc_resigned" else 0
            )
            cell_summaries[key] = {"p50_ms": wall_ms}
            rows.append(
                {
                    "placement": placement,
                    "provenance": "preserved",
                    "signature": signature,
                    "wall_ms": wall_ms,
                    "passed": True,
                    "factor_setup": {"passed": True},
                }
            )
    return {
        "experiment": {
            "name": "native-sender-placement-signature-factorial"
        },
        "metrics": {
            "cell_summaries": cell_summaries,
            "factor_deltas": {
                "placement": {
                    "contrast": "atomic_replace_minus_direct_copy",
                    "delta_ms": {"p50_ms": 0, "count": 1},
                    "positive_blocks": 0,
                },
                "signature": {
                    "contrast": "adhoc_resigned_minus_original_linker",
                    "delta_ms": {"p50_ms": delta, "count": 1},
                    "positive_blocks": int(delta > 0),
                },
            },
        },
        "trials": rows,
        "gate": {"passed": True},
    }


class NativeSenderLaunchFactorSummaryTests(unittest.TestCase):
    def test_summary_preserves_direction_reversal(self):
        report = summarize_reports(
            [_report(100), _report(-10), _report(-20)]
        )

        self.assertTrue(report["gate"]["passed"])
        signature = report["metrics"]["factor_run_boundaries"]["signature"]
        self.assertEqual(
            signature["per_run_delta_p50_ms"],
            [100, -10, -20],
        )
        self.assertFalse(signature["direction_consistent_across_run_p50s"])


if __name__ == "__main__":
    unittest.main()
