import unittest

from paper.analysis.paired_diagnostic_stats import summarize


class PairedDiagnosticStatsTests(unittest.TestCase):
    @staticmethod
    def _payload(view, right_wins=False):
        rows = []
        for family_index in range(7):
            for case_index in range(18):
                exact = not right_wins or family_index != 0 or view == "right"
                rows.append(
                    {
                        "case_id": f"family-{family_index}-case-{case_index}",
                        "fault_mode": f"family-{family_index}",
                        "view": view,
                        "predicted": {"boundary": f"b-{family_index}"},
                        "exact": exact,
                        "boundary_exact": exact,
                        "status_exact": exact,
                        "citation_entailment_valid": exact,
                    }
                )
        return {"rows": rows}

    def test_reports_template_directions_without_p_values(self):
        result = summarize(
            self._payload("left", right_wins=True),
            self._payload("right", right_wins=True),
            "left",
            "right",
        )
        self.assertEqual(result["paired_cases"], 126)
        self.assertEqual(result["fault_family_templates"], 7)
        self.assertEqual(
            result["metrics"]["exact"]["template_directions"],
            {"left_higher": 0, "right_higher": 1, "equal": 6},
        )
        self.assertNotIn("case_level_exact_mcnemar_p", result["metrics"]["exact"])

    def test_rejects_incomplete_pairing(self):
        with self.assertRaisesRegex(ValueError, "expected 126 paired cases"):
            summarize({"rows": []}, {"rows": []}, "left", "right")


if __name__ == "__main__":
    unittest.main()
