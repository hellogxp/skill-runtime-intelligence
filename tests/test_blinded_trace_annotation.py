import unittest

from experiments.semantic_diagnosis.prepare_blinded_trace_holdout import build_blinded_holdout
from experiments.semantic_diagnosis.run_blinded_trace_annotation import _prompt, _score
from experiments.semantic_diagnosis.summarize_blinded_trace_annotations import summarize


class BlindedTraceAnnotationTests(unittest.TestCase):
    def setUp(self):
        self.case = {
            "case_id": "case-1",
            "source": "deidentified_real_skill_run",
            "evidence": [{"evidence_id": "E1", "kind": "run_state", "status": "completed"}],
            "expected_findings": [{"code": "lifecycle_evidence_gap", "stage": "activation", "source_evidence_grade": "derived"}],
            "label_origin": "production_deterministic_diagnostic_candidate",
        }

    def test_blinding_removes_candidate_labels(self):
        report = build_blinded_holdout({"cases": [self.case]})
        self.assertTrue(report["gate"]["passed"])
        self.assertNotIn("expected_findings", report["cases"][0])
        self.assertNotIn("label_origin", report["cases"][0])

    def test_prompt_does_not_contain_hidden_label(self):
        blinded = {key: self.case[key] for key in ("case_id", "source", "evidence")}
        self.assertNotIn("production_deterministic", _prompt(blinded))

    def test_score_rejects_unknown_citation(self):
        parsed = {"findings": [{"code": "runtime_failure", "stage": "execution", "citations": ["missing"]}],
                  "abstain": False, "uncertainty_reason": "none", "causal_proven": False, "confidence_0_100": 80}
        self.assertFalse(_score(self.case, parsed, 1.0)["citation_id_valid"])

    def test_reveal_summary_preserves_disagreement(self):
        reference = {"cases": [self.case]}
        first = {"rows": [{"case_id": "case-1", "status": "completed", "signature": [["lifecycle_evidence_gap", "activation"]], "abstain": False}]}
        second = {"rows": [{"case_id": "case-1", "status": "completed", "signature": [], "abstain": True}]}
        result = summarize(reference, first, second)
        self.assertEqual(result["summary"]["annotator_exact_agreement"], 0)
        self.assertEqual(result["summary"]["strict_consensus_cases"], 0)


if __name__ == "__main__":
    unittest.main()
