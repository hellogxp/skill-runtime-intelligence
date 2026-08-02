import unittest

from experiments.semantic_diagnosis.prepare_real_failure_holdout import _case
from experiments.semantic_diagnosis.run_real_failure_model_study import (
    _citation_entails,
    _graph_baseline,
    _signature,
)


class RealFailureSemanticStudyTests(unittest.TestCase):
    def test_citation_entailment_rejects_valid_id_with_wrong_relation(self):
        evidence = [
            {"evidence_id": "E1", "kind": "stage_state", "stage": "resources", "status": "not_observed"},
            {"evidence_id": "E2", "kind": "stage_state", "stage": "execution", "status": "observed"},
            {"evidence_id": "E3", "kind": "stage_state", "stage": "request", "status": "observed"},
        ]
        finding = {"code": "lifecycle_evidence_gap", "stage": "resources", "source_evidence_grade": "derived", "citations": ["E1", "E2"]}
        self.assertTrue(_citation_entails(finding, evidence))
        finding["citations"] = ["E1", "E3"]
        self.assertFalse(_citation_entails(finding, evidence))

    def test_deidentified_case_omits_source_content_and_graph_matches(self):
        detail = {
            "skill_run_id": "secret-run-id",
            "status": "interrupted",
            "session_completeness": "partial",
            "stage_summary": [
                {"stage": "request", "status": "observed", "event_count": 1, "capability": "native", "evidence_grade": "observed"},
                {"stage": "discovery", "status": "not_observed", "event_count": 0, "capability": "derived", "evidence_grade": "derived"},
                {"stage": "activation", "status": "observed", "event_count": 1, "capability": "native", "evidence_grade": "observed"},
            ],
            "events": [
                {"event_type": "skill.activated", "stage": "activation", "status": "succeeded", "evidence_grade": "observed", "summary": "private"}
            ],
            "findings": [
                {"code": "lifecycle_evidence_gap", "stage": "discovery", "evidence_grade": "derived"},
                {"code": "run_incomplete", "stage": "outcome", "evidence_grade": "observed"},
            ],
        }
        case = _case(detail, "real-holdout-001")
        serialized = str(case)
        self.assertNotIn("secret-run-id", serialized)
        self.assertNotIn("private", serialized)
        predicted = {_signature(item) for item in _graph_baseline(case)["findings"]}
        expected = {_signature(item) for item in case["expected_findings"]}
        self.assertEqual(expected, predicted)

    def test_event_type_is_sanitized(self):
        detail = {
            "status": "completed",
            "session_completeness": "complete",
            "stage_summary": [],
            "events": [
                {"event_type": "private payload", "stage": "execution", "status": "failed", "evidence_grade": "observed"}
            ],
            "findings": [
                {"code": "runtime_failure", "stage": "execution", "evidence_grade": "observed"}
            ],
        }
        case = _case(detail, "real-holdout-001")
        self.assertEqual("unknown", case["evidence"][2]["event_type"])


if __name__ == "__main__":
    unittest.main()
