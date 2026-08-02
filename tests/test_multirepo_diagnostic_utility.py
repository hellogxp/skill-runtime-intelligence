import unittest

from experiments.external_validity.prepare_diagnostic_holdout import _gold, _graph_candidate, _panorama_evidence
from experiments.external_validity.run_diagnostic_utility_study import (
    _citation_entails,
    _evidence,
    _prompt,
)


class MultirepoDiagnosticUtilityTests(unittest.TestCase):
    def _row(self, mode, boundary, verifier="failed", reported="failure"):
        statuses = []
        stages = ("instructions", "resources", "execution", "artifacts", "outcome")
        for stage in stages:
            if boundary == "none": status = "observed"
            elif stages.index(stage) < stages.index(boundary): status = "observed"
            elif stage == boundary: status = "not_verified" if mode == "outcome_unverified" else "failed"
            else: status = "not_observed"
            statuses.append({"stage": stage, "status": status, "grade": "experimental"})
        return {"fault_mode": mode, "gold_boundary": boundary, "gold_trace": statuses,
                "gold_reported_status": reported, "gold_verifier_status": verifier}

    def test_graph_candidate_covers_failure_and_conflict(self):
        failure = self._row("resource_missing", "resources")
        self.assertEqual(_graph_candidate(_panorama_evidence(failure))["diagnosis_status"], "observed_failure")
        conflict = self._row("verifier_conflict", "outcome", verifier="failed", reported="success")
        self.assertEqual(_graph_candidate(_panorama_evidence(conflict))["diagnosis_status"], "verifier_conflict")

    def test_entailment_requires_relation_support(self):
        row = self._row("resource_missing", "resources")
        case = {"raw_evidence": [], "panorama_evidence": _panorama_evidence(row), "graph_candidate": _graph_candidate(_panorama_evidence(row))}
        good = {"boundary": "resources", "diagnosis_status": "observed_failure", "citations": ["P02"]}
        bad = {"boundary": "resources", "diagnosis_status": "observed_failure", "citations": ["P01"]}
        self.assertTrue(_citation_entails(case, "panorama", good))
        self.assertFalse(_citation_entails(case, "panorama", bad))

    def test_entailment_always_returns_boolean_when_required_rows_are_absent(self):
        case = {"raw_evidence": [], "panorama_evidence": [{"evidence_id": "P01", "kind": "lifecycle_stage", "stage": "instructions", "status": "observed"}], "graph_candidate": {}}
        parsed = {"boundary": "none", "diagnosis_status": "verified_success", "citations": ["P01"]}
        self.assertIs(_citation_entails(case, "panorama", parsed), False)

    def test_raw_semantic_keeps_raw_records_and_adds_semantic_contract(self):
        case = {
            "raw_evidence": [{"evidence_id": "R01", "native_type": "probe.step"}],
            "panorama_evidence": [],
            "graph_candidate": {},
        }
        evidence = _evidence(case, "raw_semantic")
        self.assertEqual(evidence[0]["semantic_kind"], "lifecycle_stage")
        self.assertEqual(evidence[0]["evidence_id"], "R01")
        self.assertNotIn("Raw records use phase ordinal", _prompt(case, "raw_semantic"))

    def test_gold_statuses(self):
        self.assertEqual(_gold({"fault_mode": "clean", "gold_boundary": "none"})["diagnosis_status"], "verified_success")
        self.assertEqual(_gold({"fault_mode": "outcome_unverified", "gold_boundary": "outcome"})["diagnosis_status"], "outcome_unverified")


if __name__ == "__main__":
    unittest.main()
