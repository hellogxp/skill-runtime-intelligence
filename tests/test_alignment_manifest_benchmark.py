import unittest

from experiments.cross_agent.alignment_manifest_benchmark import (
    evaluate_alignment,
    run_experiment,
)


class AlignmentManifestBenchmarkTests(unittest.TestCase):
    def test_contract_corpus_is_exact_and_never_allows_causal_attribution(self):
        report = run_experiment()

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["case_count"], 9)
        self.assertEqual(report["metrics"]["exact_cases"], 9)
        self.assertEqual(
            report["metrics"]["unsupported_causal_attribution_cases"],
            0,
        )

    def test_missing_alignment_key_is_not_comparable(self):
        result = evaluate_alignment(
            {
                "runs": [
                    {
                        "alignment_key": None,
                        "task_digest": "task",
                        "skill_digest": "skill",
                        "entrypoint": "explicit",
                    },
                    {
                        "alignment_key": None,
                        "task_digest": "task",
                        "skill_digest": "skill",
                        "entrypoint": "explicit",
                    },
                ]
            }
        )

        self.assertEqual(result["decision"], "not_comparable")
        self.assertEqual(result["flags"], ["alignment_key_mismatch"])
        self.assertFalse(result["causal_attribution_allowed"])


if __name__ == "__main__":
    unittest.main()
