import unittest

from experiments.real_corpus_audit.cohort_evidence_transition_benchmark import (
    _evaluate,
    _state,
)


class CohortEvidenceTransitionTests(unittest.TestCase):
    def test_state_separates_terminality_from_evidence(self):
        run = {"status": "completed"}
        detail = {
            "events": [
                {"event_type": "skill.activated", "context_only": 0},
                {"event_type": "outcome.reported", "context_only": 0},
            ]
        }

        state = _state(run, detail)

        self.assertTrue(state["terminal"])
        self.assertFalse(state["evidence_sufficient"])
        self.assertEqual(state["state"], "terminal__insufficient")

    def test_verified_outcome_closes_evidence_axis(self):
        run = {"status": "completed"}
        detail = {
            "events": [
                {"event_type": "skill.activated", "context_only": 0},
                {"event_type": "outcome.verified", "context_only": 0},
            ]
        }

        state = _state(run, detail)

        self.assertEqual(state["state"], "terminal__sufficient")

    def test_evaluate_keeps_cohort_and_aggregates_transitions(self):
        before = {
            "private-a": {"state": "nonterminal__insufficient"},
            "private-b": {"state": "terminal__insufficient"},
        }
        after = {
            "private-a": {"state": "terminal__insufficient"},
            "private-b": {"state": "terminal__sufficient"},
            "private-new": {"state": "nonterminal__insufficient"},
        }

        result = _evaluate(before, after)

        self.assertEqual(result["cohort_run_count"], 2)
        self.assertEqual(result["new_run_count"], 1)
        self.assertEqual(result["changed_state_count"], 2)
        self.assertEqual(result["changed_state_fraction"], 1.0)
        self.assertNotIn("private-a", str(result))


if __name__ == "__main__":
    unittest.main()
