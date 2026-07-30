import unittest

from experiments.real_corpus_audit.summarize_cut_policy_curve import (
    _curve,
)


def _report(interval, selected, stable):
    return {
        "experiment": {"requested_interval_seconds": interval},
        "evaluation": {
            "policies": {
                "terminal_status": {
                    "selected_run_count": selected,
                    "stable_next_interval_count": stable,
                    "changed_next_interval_count": selected - stable,
                    "missing_next_interval_count": 0,
                    "selection_fraction": selected / 10,
                    "stable_next_interval_fraction": stable / selected,
                }
            }
        },
    }


class DatasetCutPolicyCurveTests(unittest.TestCase):
    def test_groups_reports_by_wait_interval(self):
        curve = _curve(
            [
                _report(3, 8, 8),
                _report(1, 10, 9),
                _report(3, 6, 6),
                _report(1, 10, 10),
            ]
        )

        self.assertEqual(curve["interval_condition_count"], 2)
        self.assertEqual(curve["trial_count"], 4)
        self.assertEqual(
            [point["requested_interval_seconds"] for point in curve["points"]],
            [1.0, 3.0],
        )
        one_second = curve["points"][0]["policies"]["terminal_status"]
        self.assertEqual(one_second["pooled_selected_run_count"], 20)
        self.assertEqual(one_second["pooled_stable_next_interval_count"], 19)
        self.assertEqual(
            curve["points"][1]["trial_count"],
            2,
        )


if __name__ == "__main__":
    unittest.main()
