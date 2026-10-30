import json
import tempfile
import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.analyze_deny_only_hybrid import analyze
from experiments.common import sha256_path


class DenyOnlyHybridTests(unittest.TestCase):
    def test_hybrid_can_only_remove_model_allows(self):
        cases_path = Path(
            "experiments/diagnostic_usefulness/"
            "causal_claim_holdout_v2.jsonl"
        )
        report = {
            "schema_version": "sri.experiment.claim-output-mode-study.v1",
            "experiment": {
                "dataset_sha256": sha256_path(cases_path),
                "model": "test/model",
            },
            "trials": [
                {
                    "case_id": "holdout_effect_triggered",
                    "mode": "structured",
                    "status": "completed",
                    "predicted_claim_kind": "descriptive",
                    "predicted_allowed": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            report_path = Path(directory) / "report.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            result = analyze(report_path, cases_path)

        self.assertLessEqual(
            result["metrics"]["hybrid_false_allows"],
            result["metrics"]["baseline_false_allows"],
        )
        self.assertEqual(result["cases"][0]["hybrid_allowed"], False)


if __name__ == "__main__":
    unittest.main()
