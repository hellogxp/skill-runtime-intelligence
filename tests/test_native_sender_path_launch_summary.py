import unittest

from experiments.product_lifecycle.summarize_native_path_launch_reports import (
    summarize_reports,
)


def _report(value):
    cells = (
        "published:stable_path",
        "rebuilt:stable_path",
        "published:fresh_path_copy",
        "rebuilt:fresh_path_copy",
    )
    trials = []
    for key in cells:
        artifact, condition = key.split(":")
        trials.append(
            {
                "artifact": artifact,
                "condition": condition,
                "wall_ms": value + (10 if "fresh" in condition else 0),
                "passed": True,
            }
        )
    return {
        "experiment": {
            "name": "native-sender-path-reuse-launch-sensitivity"
        },
        "metrics": {
            "summaries": {
                key: {"p50_ms": value}
                for key in cells
            },
            "paired_path_deltas": {
                artifact: {
                    "positive_blocks": 1,
                    "fresh_minus_stable_ms": {"count": 1},
                }
                for artifact in ("published", "rebuilt")
            },
        },
        "trials": trials,
        "gate": {"passed": True},
    }


class NativeSenderPathLaunchSummaryTests(unittest.TestCase):
    def test_three_report_summary_passes_integrity_gate(self):
        report = summarize_reports([_report(1), _report(2), _report(3)])

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["report_count"], 3)
        self.assertEqual(report["metrics"]["total_trials"], 12)
        self.assertEqual(
            report["metrics"]["paired_directions"]["published"],
            {"fresh_slower_blocks": 3, "total_blocks": 3},
        )


if __name__ == "__main__":
    unittest.main()
