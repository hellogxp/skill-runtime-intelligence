import unittest

from experiments.diagnostic_usefulness.run_claim_output_mode_study import (
    _metrics,
    _parse_structured,
)


class ClaimOutputModeStudyTests(unittest.TestCase):
    def test_parses_structured_enum(self):
        result = _parse_structured(
            '{"claim_kind":"source_attribution","allowed":true}'
        )

        self.assertEqual(result["claim_kind"], "source_attribution")
        self.assertTrue(result["model_allowed"])

    def test_metrics_count_invalid_as_incorrect(self):
        rows = [
            {
                "mode": "structured",
                "status": "parse_error",
            },
            {
                "mode": "free_text",
                "status": "completed",
                "claim_kind_correct": False,
                "guard_decision_correct": True,
                "false_allow": False,
                "false_deny": False,
                "predicted_claim_kind": "unknown",
                "model_allowed_agrees_guard": None,
                "elapsed_ms": 10,
                "session_id_sha256": "session",
            },
        ]

        metrics = _metrics(rows)

        self.assertEqual(
            metrics["by_mode"]["structured"][
                "claim_kind_intention_to_treat_accuracy"
            ],
            0.0,
        )
        self.assertEqual(
            metrics["by_mode"]["free_text"]["unknown_predictions"], 1
        )


if __name__ == "__main__":
    unittest.main()
