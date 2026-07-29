import unittest

from skill_runtime_intelligence.diagnostics import diagnose_skill_run


def stage_summary(**statuses):
    result = []
    for stage in (
        "request",
        "discovery",
        "activation",
        "instructions",
        "resources",
        "execution",
        "artifacts",
        "outcome",
    ):
        status = statuses.get(stage, "observed")
        result.append(
            {
                "stage": stage,
                "status": status,
                "capability": "unsupported" if status == "unsupported" else "observed",
                "event_count": 1 if status in {"observed", "failed"} else 0,
                "evidence_grade": "observed" if status in {"observed", "failed"} else None,
            }
        )
    return result


class DiagnosticsTests(unittest.TestCase):
    def test_reports_gap_only_when_later_evidence_exists(self):
        run = {
            "skill_run_id": "run-gap",
            "status": "completed",
            "session_completeness": "complete",
            "stage_summary": stage_summary(
                discovery="unsupported",
                activation="not_observed",
            ),
            "events": [
                {
                    "stage": "outcome",
                    "event_type": "outcome.verified",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Test passed",
                }
            ],
        }

        findings = diagnose_skill_run(run)

        self.assertEqual([item["code"] for item in findings], ["lifecycle_evidence_gap"])
        self.assertEqual(findings[0]["stage"], "activation")
        self.assertEqual(findings[0]["evidence_grade"], "derived")

    def test_unsupported_stage_is_not_a_gap(self):
        run = {
            "skill_run_id": "run-unsupported",
            "status": "completed",
            "session_completeness": "complete",
            "stage_summary": stage_summary(discovery="unsupported"),
            "events": [
                {
                    "stage": "outcome",
                    "event_type": "outcome.verified",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Test passed",
                }
            ],
        }

        self.assertEqual(diagnose_skill_run(run), [])

    def test_failure_and_incomplete_run_remain_separate_findings(self):
        run = {
            "skill_run_id": "run-failed",
            "status": "incomplete",
            "session_completeness": "partial",
            "stage_summary": stage_summary(outcome="not_observed"),
            "events": [
                {
                    "stage": "execution",
                    "event_type": "tool.failed",
                    "status": "failed",
                    "evidence_grade": "observed",
                    "summary": "Renderer exited with status 1",
                }
            ],
        }

        findings = diagnose_skill_run(run)

        self.assertEqual(
            [item["code"] for item in findings],
            ["runtime_failure", "run_incomplete"],
        )
        self.assertEqual(findings[0]["stage"], "execution")
        self.assertEqual(findings[0]["evidence_grade"], "observed")

    def test_reported_outcome_is_not_presented_as_verified(self):
        run = {
            "skill_run_id": "run-reported",
            "status": "completed",
            "session_completeness": "complete",
            "stage_summary": stage_summary(discovery="unsupported"),
            "events": [
                {
                    "stage": "outcome",
                    "event_type": "outcome.reported",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Agent reported completion",
                }
            ],
        }

        findings = diagnose_skill_run(run)

        self.assertEqual([item["code"] for item in findings], ["outcome_unverified"])
        self.assertEqual(findings[0]["severity"], "info")

    def test_earlier_lifecycle_gap_sorts_before_later_failure(self):
        run = {
            "skill_run_id": "run-order",
            "status": "interrupted",
            "session_completeness": "partial",
            "stage_summary": stage_summary(
                discovery="unsupported",
                resources="not_observed",
                execution="failed",
            ),
            "events": [
                {
                    "stage": "execution",
                    "event_type": "tool.failed",
                    "status": "failed",
                    "evidence_grade": "observed",
                    "summary": "Tool failed after the resource boundary",
                }
            ],
        }

        findings = diagnose_skill_run(run)

        self.assertEqual(findings[0]["code"], "lifecycle_evidence_gap")
        self.assertEqual(findings[0]["stage"], "resources")


if __name__ == "__main__":
    unittest.main()
