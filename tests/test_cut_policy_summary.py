import unittest

from experiments.real_corpus_audit.summarize_cut_policy_reports import (
    _aggregate,
)


def _report(selected, stable, selection_fraction):
    return {
        "evaluation": {
            "policies": {
                "terminal_status": {
                    "selected_run_count": selected,
                    "stable_next_interval_count": stable,
                    "changed_next_interval_count": selected - stable,
                    "missing_next_interval_count": 0,
                    "selection_fraction": selection_fraction,
                    "stable_next_interval_fraction": stable / selected,
                }
            }
        }
    }


class DatasetCutPolicySummaryTests(unittest.TestCase):
    def test_aggregates_counts_and_trial_ranges(self):
        aggregate = _aggregate(
            [_report(8, 8, 0.8), _report(6, 3, 0.6)]
        )
        terminal = aggregate["policies"]["terminal_status"]

        self.assertEqual(aggregate["trial_count"], 2)
        self.assertEqual(terminal["pooled_selected_run_count"], 14)
        self.assertEqual(terminal["pooled_stable_next_interval_count"], 11)
        self.assertEqual(
            terminal["pooled_stable_next_interval_fraction"],
            11 / 14,
        )
        self.assertEqual(
            terminal["selection_fraction_across_trials"]["minimum"],
            0.6,
        )
        self.assertEqual(
            terminal["stable_fraction_across_trials"]["maximum"],
            1.0,
        )


if __name__ == "__main__":
    unittest.main()
