import json
import tempfile
import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.summarize_claim_output_studies import (
    summarize,
)


class ClaimOutputModeSummaryTests(unittest.TestCase):
    def test_preserves_model_strata_and_safety_counts(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, model in enumerate(("provider/a", "provider/b")):
                path = Path(directory) / f"{index}.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": (
                                "sri.experiment.claim-output-mode-study.v1"
                            ),
                            "experiment": {
                                "dataset_sha256": "same",
                                "model": model,
                            },
                            "metrics": {
                                "structured_minus_free_text_kind_accuracy": 0.5,
                                "by_mode": {
                                    "structured": {
                                        "false_allows": index,
                                        "model_guard_disagreements": 1,
                                    },
                                    "free_text": {"false_denies": 2},
                                },
                            },
                            "gate": {"passed": index == 0},
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)

            result = summarize(paths)

        self.assertEqual(result["metrics"]["study_count"], 2)
        self.assertEqual(result["metrics"]["structured_false_allow_count"], 1)
        self.assertEqual(result["metrics"]["free_text_false_deny_count"], 4)
        self.assertFalse(result["gates"]["confirmatory_safety_ready"])


if __name__ == "__main__":
    unittest.main()
