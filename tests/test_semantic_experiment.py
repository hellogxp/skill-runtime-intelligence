import copy
import unittest
from pathlib import Path

from experiments.common import load_jsonl
from experiments.semantic_diagnosis.run_benchmark import (
    _expected,
    _relational_anchors,
    _relational_template_prediction,
)


ROOT = Path(__file__).resolve().parents[1]
CASES = ROOT / "experiments" / "runtime_diagnostics" / "cases.jsonl"


class RelationalTemplateExperimentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_jsonl(CASES)

    def test_ordered_anchors_distinguish_gap_from_missing_tail(self):
        by_id = {case["case_id"]: case for case in self.cases}
        gap = _relational_anchors(by_id["activation_gap"])
        missing_tail = _relational_anchors(
            by_id["missing_tail_without_later_evidence"]
        )
        unsupported = _relational_anchors(by_id["unsupported_is_not_gap"])

        self.assertEqual(
            gap["first_supported_gap_before_later_activity"],
            ("activation", "derived"),
        )
        self.assertNotIn(
            "first_supported_gap_before_later_activity",
            missing_tail,
        )
        self.assertNotIn(
            "first_supported_gap_before_later_activity",
            unsupported,
        )

    def test_prediction_does_not_read_held_out_expected_findings(self):
        by_id = {case["case_id"]: case for case in self.cases}
        query = by_id["activation_gap"]
        candidates = [case for case in self.cases if case is not query]
        expected_prediction, _ = _relational_template_prediction(query, candidates)

        mutated_query = copy.deepcopy(query)
        mutated_query["expected_findings"] = [
            {
                "code": "target_label_must_not_leak",
                "stage": "outcome",
                "evidence_grade": "experimental",
            }
        ]
        mutated_prediction, _ = _relational_template_prediction(
            mutated_query,
            candidates,
        )

        self.assertEqual(mutated_prediction, expected_prediction)
        self.assertEqual(expected_prediction, _expected(query))

    def test_novel_held_out_relation_code_is_not_invented(self):
        query = next(
            case for case in self.cases if case["case_id"] == "reported_outcome_only"
        )
        candidates = [case for case in self.cases if case is not query]

        prediction, audit = _relational_template_prediction(query, candidates)

        self.assertEqual(prediction, set())
        self.assertEqual(audit[0]["relation"], "reported_outcome_without_verifier")
        self.assertIsNone(audit[0]["selected_code"])


if __name__ == "__main__":
    unittest.main()
