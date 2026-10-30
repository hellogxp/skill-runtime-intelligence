import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.analyze_prospective_fragility_study import (
    analyze,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments" / "diagnostic_usefulness"
RESULTS = BASE / "results"
REQUIRED_RESULTS = (
    RESULTS / "structured-claim-producer-fragility-holdout-20260731.json",
    RESULTS / "fragility-review-queue-holdout-20260731.json",
    RESULTS
    / "structured-claim-selected-verifier-fragility-holdout-20260731.json",
    RESULTS / "structured-claim-random-shadow-fragility-holdout-20260731.json",
)


class ProspectiveFragilityStudyTests(unittest.TestCase):
    @unittest.skipUnless(
        all(path.is_file() for path in REQUIRED_RESULTS),
        "requires locally retained prospective study reports",
    )
    def test_fragility_queue_captures_holdout_false_allow(self):
        result = analyze(
            BASE / "causal_claim_fragility_holdout.jsonl",
            *REQUIRED_RESULTS,
        )

        self.assertEqual(result["metrics"]["baseline_false_allows"], 1)
        self.assertEqual(result["metrics"]["captured_false_allows"], 1)
        self.assertEqual(result["metrics"]["routed_false_allows"], 0)
        self.assertEqual(result["metrics"]["routed_false_denies"], 0)


if __name__ == "__main__":
    unittest.main()
