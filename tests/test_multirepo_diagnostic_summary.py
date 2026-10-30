import unittest

from experiments.external_validity.summarize_diagnostic_utility import _paired


class MultirepoDiagnosticSummaryTests(unittest.TestCase):
    def test_paired_direction_preserves_wins_and_losses(self):
        rows = [
            {"case_id": "a", "view": "raw", "status": "completed", "exact": False},
            {"case_id": "a", "view": "panorama", "status": "completed", "exact": True},
            {"case_id": "b", "view": "raw", "status": "completed", "exact": True},
            {"case_id": "b", "view": "panorama", "status": "completed", "exact": False},
        ]
        result = _paired(rows, "raw", "panorama")
        self.assertEqual(result["right_wins"], 1)
        self.assertEqual(result["right_losses"], 1)
        self.assertEqual(result["right_minus_left_exact"], 0)


if __name__ == "__main__":
    unittest.main()
