import json
import tempfile
import unittest
from pathlib import Path

from experiments.diagnostic_usefulness.summarize_model_studies import summarize


def _trial(condition, correct, session):
    return {
        "status": "completed",
        "condition": condition,
        "case_id": "case",
        "correct": correct,
        "unsupported_causal_claim": False,
        "confidence_0_100": 80,
        "elapsed_ms": 10,
        "session_id_sha256": session,
    }


class ModelDiagnosticSummaryTests(unittest.TestCase):
    def test_keeps_model_effects_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, model in enumerate(("provider/a", "provider/b")):
                path = Path(directory) / f"{index}.json"
                path.write_text(
                    json.dumps(
                        {
                            "schema_version": (
                                "sri.experiment.model-agent-usefulness-result.v1"
                            ),
                            "experiment": {
                                "dataset_sha256": "same",
                                "model": model,
                                "model_cli_version": "1",
                            },
                            "trials": [
                                _trial("raw", False, f"r{index}"),
                                _trial("panorama", True, f"p{index}"),
                            ],
                            "gate": {"passed": True},
                        }
                    ),
                    encoding="utf-8",
                )
                paths.append(path)

            result = summarize(paths)

        self.assertEqual(result["metrics"]["distinct_recorded_model_count"], 2)
        self.assertEqual(
            result["metrics"]["positive_panorama_direction_count"], 2
        )
        self.assertTrue(result["gates"]["exploratory_direction_replicated"])
        self.assertEqual(len(result["studies"]), 2)


if __name__ == "__main__":
    unittest.main()
