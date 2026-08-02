import unittest

from experiments.external_validity.analyze_reconstruction_fidelity import _telemetry_boundary, analyze


class MultirepoReconstructionFidelityTests(unittest.TestCase):
    def test_earliest_failed_stage(self):
        row = {"collector_evidence": {"event_signatures": [
            {"stage": "execution", "status": "failed"}, {"stage": "resources", "status": "failed"}]}}
        self.assertEqual(_telemetry_boundary(row), "resources")

    def test_clean_false_positive_is_separate_from_failure_recall(self):
        rows = [
            {"agent": "x", "repo_key": "r", "fault_mode": "clean", "gold_boundary": "none",
             "collector_evidence": {"session_match_count": 1, "skill_run_count": 1,
                                    "event_signatures": [{"stage": "execution", "status": "failed"}]}},
            {"agent": "x", "repo_key": "r", "fault_mode": "execution_failure", "gold_boundary": "execution",
             "collector_evidence": {"session_match_count": 1, "skill_run_count": 1,
                                    "event_signatures": [{"stage": "execution", "status": "failed"}]}},
        ]
        _, summary = analyze(rows)
        self.assertEqual(summary["x"]["failure_detection_recall"], 1.0)
        self.assertEqual(summary["x"]["clean_false_positive_rate"], 1.0)


if __name__ == "__main__":
    unittest.main()
