import json
import tempfile
import unittest
from pathlib import Path

from experiments.common import sha256_path
from experiments.diagnostic_usefulness.analyze_cross_model_semantic_guard import (
    analyze_pair,
)


class CrossModelSemanticGuardTests(unittest.TestCase):
    def test_cross_model_guard_is_deny_only(self):
        cases_path = Path(
            "experiments/diagnostic_usefulness/"
            "causal_claim_discourse_holdout.jsonl"
        )
        digest = sha256_path(cases_path)

        def report(model, claim_kind, allowed):
            return {
                "schema_version": (
                    "sri.experiment.claim-output-mode-study.v1"
                ),
                "experiment": {
                    "dataset_sha256": digest,
                    "model": model,
                },
                "trials": [
                    {
                        "case_id": "discourse_effect_hedged",
                        "mode": "structured",
                        "status": "completed",
                        "predicted_claim_kind": claim_kind,
                        "predicted_allowed": allowed,
                    }
                ],
            }

        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            first_path.write_text(
                json.dumps(report("model/a", "descriptive", True)),
                encoding="utf-8",
            )
            second_path.write_text(
                json.dumps(
                    report("model/b", "skill_outcome_effect", False)
                ),
                encoding="utf-8",
            )
            result = analyze_pair(first_path, second_path, cases_path)

        first_direction = result["directions"][0]
        row = next(
            item
            for item in first_direction["cases"]
            if item["case_id"] == "discourse_effect_hedged"
        )
        self.assertTrue(row["producer_allowed"])
        self.assertFalse(row["hybrid_allowed"])
        self.assertFalse(row["exact_kind_consensus_allowed"])
        self.assertEqual(
            first_direction["metrics"]["hybrid_false_allows"], 0
        )

    def test_same_model_id_is_rejected(self):
        cases_path = Path(
            "experiments/diagnostic_usefulness/"
            "causal_claim_discourse_holdout.jsonl"
        )
        digest = sha256_path(cases_path)
        report = {
            "schema_version": "sri.experiment.claim-output-mode-study.v1",
            "experiment": {
                "dataset_sha256": digest,
                "model": "model/a",
            },
            "trials": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            first_path = Path(directory) / "first.json"
            second_path = Path(directory) / "second.json"
            first_path.write_text(json.dumps(report), encoding="utf-8")
            second_path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(ValueError):
                analyze_pair(first_path, second_path, cases_path)


if __name__ == "__main__":
    unittest.main()
