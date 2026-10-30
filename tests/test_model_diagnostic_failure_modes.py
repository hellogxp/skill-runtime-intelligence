import json
import tempfile
import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.analyze_model_failure_modes import (
    analyze,
)


class ModelDiagnosticFailureModeTests(unittest.TestCase):
    def test_invalid_response_is_incorrect_in_family_audit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = root / "cases.jsonl"
            cases.write_text(
                json.dumps(
                    {
                        "case_id": "gap",
                        "expected_findings": [
                            {
                                "code": "lifecycle_evidence_gap",
                                "stage": "resources",
                            }
                        ],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            result_path = root / "result.json"
            result_path.write_text(
                json.dumps(
                    {
                        "schema_version": (
                            "sri.experiment.model-agent-usefulness-result.v1"
                        ),
                        "experiment": {
                            "dataset_sha256": "digest",
                            "model": "provider/model",
                        },
                        "trials": [
                            {
                                "case_id": "gap",
                                "condition": "panorama",
                                "status": "parse_error",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = analyze([result_path], cases)

        bucket = result["reports"][0]["by_finding_family"]["panorama"][
            "lifecycle_evidence_gap"
        ]
        self.assertEqual(bucket["planned"], 1)
        self.assertEqual(bucket["parse_or_execution_errors"], 1)
        self.assertEqual(bucket["intention_to_treat_accuracy"], 0.0)


if __name__ == "__main__":
    unittest.main()
