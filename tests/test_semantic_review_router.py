import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.analyze_semantic_review_router import (
    analyze,
)

ROOT = Path(__file__).resolve().parents[1]
REPORT = (
    ROOT
    / "experiments"
    / "diagnostic_usefulness"
    / "results"
    / "cross-model-semantic-guard-challenge-20260731.json"
)


class SemanticReviewRouterTests(unittest.TestCase):
    @unittest.skipUnless(
        REPORT.is_file(),
        "requires a locally retained cross-model study report",
    )
    def test_router_never_uses_local_kind_as_final_decision(self):
        result = analyze([REPORT])

        self.assertEqual(result["metrics"]["baseline_false_allows"], 1)
        self.assertEqual(result["metrics"]["captured_false_allows"], 1)
        self.assertEqual(result["metrics"]["routed_false_allows"], 0)
        self.assertEqual(result["metrics"]["routed_false_denies"], 0)


if __name__ == "__main__":
    unittest.main()
