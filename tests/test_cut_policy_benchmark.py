import unittest
from datetime import datetime, timedelta, timezone

from experiments.real_corpus_audit.cut_policy_benchmark import (
    _evaluate_policies,
)


def _state(status, latest_at, fingerprint):
    return {
        "status": status,
        "latest_at": latest_at,
        "fingerprint": fingerprint,
    }


class DatasetCutPolicyTests(unittest.TestCase):
    def test_policies_separate_terminal_watermark_and_quiescence(self):
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        old = now - timedelta(seconds=60)
        recent = now - timedelta(seconds=2)
        before = {
            "stable-terminal": _state("completed", old, "same"),
            "changed-terminal": _state("completed", old, "before"),
            "stable-active": _state("incomplete", recent, "active"),
        }
        selection = {
            "stable-terminal": _state("completed", old, "same"),
            "changed-terminal": _state("completed", old, "selection"),
            "stable-active": _state("incomplete", recent, "active"),
        }
        outcome = {
            "stable-terminal": _state("completed", old, "same"),
            "changed-terminal": _state("completed", old, "outcome"),
            "stable-active": _state("incomplete", recent, "active"),
            "new": _state("incomplete", recent, "new"),
        }

        result = _evaluate_policies(
            before,
            selection,
            outcome,
            now,
            watermark_seconds=30,
            observed_quiescence_seconds=2,
        )

        self.assertEqual(result["selection_snapshot_run_count"], 3)
        self.assertEqual(result["new_run_count_in_outcome_snapshot"], 1)
        self.assertEqual(
            result["policies"]["terminal_status"]["selected_run_count"],
            2,
        )
        self.assertEqual(
            result["policies"]["event_watermark"]["selected_run_count"],
            2,
        )
        self.assertEqual(
            result["policies"]["observed_quiescence"]["selected_run_count"],
            2,
        )
        self.assertEqual(
            result["policies"]["terminal_and_watermark"][
                "selected_run_count"
            ],
            2,
        )
        self.assertEqual(
            result["policies"]["terminal_watermark_and_quiescence"][
                "selected_run_count"
            ],
            1,
        )
        self.assertEqual(
            result["policies"]["terminal_status"][
                "changed_next_interval_count"
            ],
            1,
        )
        self.assertEqual(
            result["policies"]["observed_quiescence"][
                "changed_next_interval_count"
            ],
            0,
        )
        self.assertEqual(
            result["policies"]["terminal_watermark_and_quiescence"][
                "changed_next_interval_count"
            ],
            0,
        )

    def test_empty_selection_has_no_stability_fraction(self):
        now = datetime(2026, 7, 29, tzinfo=timezone.utc)
        result = _evaluate_policies(
            {},
            {},
            {},
            now,
            watermark_seconds=30,
            observed_quiescence_seconds=2,
        )

        self.assertIsNone(
            result["policies"]["terminal_status"][
                "stable_next_interval_fraction"
            ]
        )


if __name__ == "__main__":
    unittest.main()
