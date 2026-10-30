import io
import json
import unittest
from unittest import mock

from experiments.diagnostic_usefulness.run_model_study import (
    _metrics,
    _run_openai_compatible_trial,
    _parse_json_object,
)


class ModelDiagnosticUsefulnessTests(unittest.TestCase):
    def test_parses_bounded_structured_response(self):
        parsed = _parse_json_object(
            '{"first_boundary":"resources","causal_proven":false,'
            '"confidence_0_100":91,"evidence_reference":"missing resource"}'
        )

        self.assertEqual(parsed["first_boundary"], "resources")
        self.assertFalse(parsed["causal_proven"])
        self.assertEqual(parsed["confidence_0_100"], 91)

    def test_rejects_invalid_stage(self):
        with self.assertRaises(ValueError):
            _parse_json_object(
                '{"first_boundary":"model_thought","causal_proven":false,'
                '"confidence_0_100":50}'
            )

    def test_metrics_keep_conditions_and_session_independence_visible(self):
        rows = [
            {
                "status": "completed",
                "condition": "raw",
                "case_id": "a",
                "correct": False,
                "unsupported_causal_claim": False,
                "confidence_0_100": 80,
                "elapsed_ms": 20,
                "session_id_sha256": "one",
            },
            {
                "status": "completed",
                "condition": "panorama",
                "case_id": "a",
                "correct": True,
                "unsupported_causal_claim": False,
                "confidence_0_100": 90,
                "elapsed_ms": 10,
                "session_id_sha256": "two",
            },
        ]

        metrics = _metrics(rows)

        self.assertEqual(metrics["unique_session_count"], 2)
        self.assertEqual(
            metrics["panorama_minus_raw_complete_case_accuracy"], 1.0
        )
        self.assertEqual(
            metrics["panorama_minus_raw_intention_to_treat_accuracy"], 1.0
        )
        self.assertEqual(
            metrics["matched_case_direction"]["panorama_wins"], 1
        )

    @mock.patch(
        "experiments.diagnostic_usefulness.run_model_study.urllib.request.urlopen"
    )
    def test_openai_compatible_backend_uses_schema_and_scores_response(
        self,
        urlopen,
    ):
        urlopen.return_value = io.BytesIO(
            json.dumps(
                {
                    "id": "response-1",
                    "choices": [
                        {
                            "message": {
                                "content": (
                                    '{"first_boundary":"resources",'
                                    '"causal_proven":false,'
                                    '"confidence_0_100":95,'
                                    '"evidence_reference":"resource event"}'
                                )
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 8},
                }
            ).encode("utf-8")
        )

        row = _run_openai_compatible_trial(
            {
                "case_id": "resource_failure",
                "condition": "raw",
                "gold_stage": "resources",
                "prompt_sha256": "digest",
                "prompt": "diagnose",
            },
            model="local-model",
            api_base="http://127.0.0.1:8000/v1",
            api_key=None,
            server_version="test-server",
            timeout_seconds=3,
            max_tokens=128,
            temperature=0.0,
            enable_thinking=False,
        )

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(
            payload["response_format"]["json_schema"]["schema"][
                "additionalProperties"
            ],
            False,
        )
        self.assertEqual(row["status"], "completed")
        self.assertTrue(row["correct"])
        self.assertFalse(row["unsupported_causal_claim"])
        self.assertIsNotNone(row["session_id_sha256"])


if __name__ == "__main__":
    unittest.main()
