import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.summarize_prospective_fragility_studies import (
    summarize,
)

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "experiments" / "diagnostic_usefulness" / "results"
REQUIRED_RESULTS = (
    RESULTS / "prospective-fragility-study-20260731.json",
    RESULTS / "prospective-fragility-study-v2-20260731.json",
)


class ProspectiveFragilitySummaryTests(unittest.TestCase):
    @unittest.skipUnless(
        all(path.is_file() for path in REQUIRED_RESULTS),
        "requires locally retained prospective study reports",
    )
    def test_two_holdouts_are_not_promotion_ready(self):
        result = summarize(REQUIRED_RESULTS)

        self.assertFalse(result["promotion_ready"])
        self.assertEqual(result["metrics"]["holdout_count"], 2)


if __name__ == "__main__":
    unittest.main()
