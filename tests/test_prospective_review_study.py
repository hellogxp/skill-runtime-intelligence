import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.analyze_prospective_review_study import (
    analyze,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "experiments" / "diagnostic_usefulness"
RESULTS = BASE / "results"
REQUIRED_RESULTS = (
    RESULTS / "structured-claim-producer-routing-holdout-20260731.json",
    RESULTS / "prospective-review-queue-routing-holdout-20260731.json",
    RESULTS / "structured-claim-selected-verifier-routing-holdout-20260731.json",
    RESULTS / "structured-claim-shadow-verifier-routing-holdout-20260731.json",
)


class ProspectiveReviewStudyTests(unittest.TestCase):
    @unittest.skipUnless(
        all(path.is_file() for path in REQUIRED_RESULTS),
        "requires locally retained prospective study reports",
    )
    def test_frozen_router_and_shadow_trade_safety_for_usability(self):
        result = analyze(
            BASE / "causal_claim_routing_holdout.jsonl",
            *REQUIRED_RESULTS,
        )

        self.assertEqual(result["metrics"]["router_missed_false_allows"], 2)
        self.assertEqual(result["metrics"]["routed_false_denies"], 0)
        self.assertEqual(result["metrics"]["always_on_false_allows"], 0)
        self.assertEqual(result["metrics"]["always_on_false_denies"], 1)


if __name__ == "__main__":
    unittest.main()
