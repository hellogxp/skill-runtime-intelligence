import json
import tempfile
import unittest
from pathlib import Path

from experiments.common import sha256_path
from experiments.diagnostic_usefulness.prepare_fragility_review_queue import (
    prepare,
)


class FragilityReviewQueueTests(unittest.TestCase):
    def test_selected_and_shadow_sets_are_disjoint_and_deterministic(self):
        cases_path = Path(
            "experiments/diagnostic_usefulness/"
            "causal_claim_fragility_holdout.jsonl"
        )
        cases = [
            json.loads(line)
            for line in cases_path.read_text().splitlines()
        ]
        producer = {
            "experiment": {"dataset_sha256": sha256_path(cases_path)},
            "trials": [
                {
                    "case_id": case["case_id"],
                    "mode": "structured",
                    "status": "completed",
                    "predicted_claim_kind": case["expected_claim_kind"],
                    "predicted_allowed": case["expected_allowed"],
                }
                for case in cases
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            producer_path = Path(directory) / "producer.json"
            producer_path.write_text(json.dumps(producer), encoding="utf-8")
            first = prepare(cases_path, producer_path, 1.0, 0.25, 7)
            second = prepare(cases_path, producer_path, 1.0, 0.25, 7)

        selected = {case["case_id"] for case in first[1]}
        shadow = {case["case_id"] for case in first[2]}
        self.assertFalse(selected & shadow)
        self.assertEqual(
            [case["case_id"] for case in first[2]],
            [case["case_id"] for case in second[2]],
        )


if __name__ == "__main__":
    unittest.main()
