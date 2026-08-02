import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.causal_claim_classifier_benchmark import (
    classify_claim,
    classify_claim_fail_closed,
    classify_claim_fail_closed_v3,
    run_benchmark,
)


class CausalClaimClassifierBenchmarkTests(unittest.TestCase):
    def test_evidence_disclaimer_is_descriptive(self):
        result = classify_claim(
            "This does not prove that the Skill caused the outcome."
        )

        self.assertEqual(result["claim_kind"], "descriptive")

    def test_source_attribution_is_not_direct_effect(self):
        result = classify_claim(
            "The agent reported that the Skill caused the outcome."
        )

        self.assertEqual(result["claim_kind"], "source_attribution")

    def test_development_contract_corpus(self):
        report = run_benchmark(
            Path(
                "experiments/diagnostic_usefulness/"
                "causal_claim_cases.jsonl"
            )
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["false_allows"], 0)
        self.assertEqual(report["metrics"]["false_denies"], 0)

    def test_fail_closed_policy_abstains_on_unrecognized_causal_synonym(self):
        result = classify_claim_fail_closed(
            "Skill activation brought about the failure."
        )

        self.assertEqual(result["claim_kind"], "unknown")

    def test_fail_closed_challenge_has_no_false_allows(self):
        report = run_benchmark(
            Path(
                "experiments/diagnostic_usefulness/"
                "causal_claim_challenge_cases.jsonl"
            ),
            corpus_role="post-freeze-challenge",
            classifier_policy="fail-closed-v2",
        )

        self.assertTrue(report["gates"]["guard_safety_no_false_allow"])
        self.assertEqual(report["metrics"]["false_allows"], 0)

    def test_v3_covers_known_challenge_synonyms(self):
        self.assertEqual(
            classify_claim_fail_closed_v3(
                "Skill activation brought about the failure."
            )["claim_kind"],
            "skill_outcome_effect",
        )

    def test_v3_is_not_retuned_to_new_holdout(self):
        report = run_benchmark(
            Path(
                "experiments/diagnostic_usefulness/"
                "causal_claim_holdout_v2.jsonl"
            ),
            corpus_role="post-freeze-challenge",
            classifier_policy="fail-closed-v3",
        )

        self.assertEqual(report["metrics"]["case_count"], 16)
        self.assertGreater(
            report["metrics"]["false_denies"]
            + report["metrics"]["false_allows"],
            0,
        )


if __name__ == "__main__":
    unittest.main()
