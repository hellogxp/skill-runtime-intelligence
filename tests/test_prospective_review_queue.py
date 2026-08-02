import json
import tempfile
import unittest
from pathlib import Path

from experiments.common import sha256_path
from experiments.diagnostic_usefulness.prepare_prospective_review_queue import (
    prepare,
)


class ProspectiveReviewQueueTests(unittest.TestCase):
    def test_unknown_local_wording_does_not_select_review(self):
        cases_path = Path(
            "experiments/diagnostic_usefulness/"
            "causal_claim_routing_holdout.jsonl"
        )
        producer = {
            "experiment": {"dataset_sha256": sha256_path(cases_path)},
            "trials": [
                {
                    "case_id": "routing_effect_precipitated",
                    "mode": "structured",
                    "status": "completed",
                    "predicted_claim_kind": "descriptive",
                    "predicted_allowed": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            producer_path = Path(directory) / "producer.json"
            producer_path.write_text(json.dumps(producer), encoding="utf-8")
            report, _ = prepare(cases_path, producer_path)

        row = next(
            item
            for item in report["selections"]
            if item["case_id"] == "routing_effect_precipitated"
        )
        self.assertEqual(row["local_router_claim_kind"], "unknown")
        self.assertFalse(row["selected"])


if __name__ == "__main__":
    unittest.main()
