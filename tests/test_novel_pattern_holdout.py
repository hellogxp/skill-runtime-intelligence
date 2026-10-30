import unittest

from experiments.semantic_diagnosis.prepare_novel_pattern_holdout import build_cases


class NovelPatternHoldoutTests(unittest.TestCase):
    def test_balanced_pairs(self):
        cases = build_cases()
        self.assertEqual(len(cases), 12)
        self.assertEqual(sum(case["anomaly_present"] for case in cases), 6)
        self.assertEqual(len({case["family"] for case in cases}), 6)


if __name__ == "__main__":
    unittest.main()
