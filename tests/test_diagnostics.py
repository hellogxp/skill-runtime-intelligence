import unittest

from skill_runtime_intelligence.diagnostics import (
    assess_skill_run,
    diagnose_skill_run,
    validate_causal_claim,
)


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
        self.assertEqual(findings[0]["causal_scope"], "none")

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
        self.assertEqual(findings[0]["causal_scope"], "none")

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
            "behavior_assessment": {"verifier_expected": True},
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

    def test_causal_scope_fails_closed_for_single_run_finding(self):
        descriptive = validate_causal_claim("none", "descriptive")
        effect = validate_causal_claim("none", "skill_outcome_effect")

        self.assertTrue(descriptive["allowed"])
        self.assertFalse(effect["allowed"])
        self.assertIn("does not authorize", effect["reason"])

    def test_experimental_scope_can_authorize_effect_estimate(self):
        result = validate_causal_claim(
            "experimental_estimate", "skill_outcome_effect"
        )

        self.assertTrue(result["allowed"])

    def test_unknown_causal_scope_fails_closed(self):
        result = validate_causal_claim("model_confident", "skill_outcome_effect")

        self.assertFalse(result["allowed"])
        self.assertIn("Unknown causal scope", result["reason"])

    def test_assessment_separates_missing_evidence_from_failure(self):
        run = {
            "skill_run_id": "run-assessment-gap",
            "status": "completed",
            "session_completeness": "incomplete",
            "activation_mode": "unknown",
            "stage_summary": stage_summary(
                discovery="unsupported",
                activation="not_observed",
            ),
            "events": [
                {
                    "stage": "instructions",
                    "event_type": "instruction.loaded",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "basis": "Exact Skill path was read",
                },
                {
                    "stage": "execution",
                    "event_type": "tool.completed",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "basis": "Tool event occurred in the active Skill scope",
                },
                {
                    "stage": "outcome",
                    "event_type": "outcome.reported",
                    "status": "reported",
                    "evidence_grade": "observed",
                    "basis": "Agent message",
                },
            ],
        }

        assessment = assess_skill_run(run)

        self.assertEqual(assessment["verdict"], "open_questions")
        self.assertEqual(assessment["evidence_grade"], "derived")
        self.assertEqual(assessment["causal_scope"], "none")
        dimensions = {
            item["dimension"]: item for item in assessment["dimensions"]
        }
        self.assertEqual(dimensions["reconstruction"]["status"], "partial_source")
        self.assertEqual(
            dimensions["runtime_failure"]["status"], "no_failure_observed"
        )
        self.assertEqual(dimensions["activation"]["status"], "unconfirmed")
        self.assertEqual(
            dimensions["outcome_verification"]["status"],
            "reported_not_verified",
        )
        checks = {item["stage"]: item for item in assessment["checks"]}
        self.assertEqual(checks["activation"]["status"], "unconfirmed")
        self.assertEqual(checks["instructions"]["status"], "matched")
        self.assertEqual(checks["execution"]["status"], "matched")
        self.assertEqual(checks["outcome"]["status"], "unconfirmed")
        self.assertIn("not causal effect", checks["execution"]["observed"])
        diagnosis = assessment["diagnosis"]
        self.assertEqual(diagnosis["status"], "no_observed_issue")
        self.assertEqual(
            diagnosis["counts"],
            {
                "confirmed_failures": 0,
                "behavior_deviations": 0,
                "verification_gaps": 0,
                "observability_limits": 2,
            },
        )
        self.assertEqual(diagnosis["attention_items"], [])
        self.assertEqual(
            {item["code"] for item in diagnosis["observability_limits"]},
            {"source_incomplete", "enablement_unconfirmed"},
        )
        self.assertEqual(
            diagnosis["conformance"]["status"], "definition_unavailable"
        )
        self.assertEqual(
            diagnosis["reasoning"]["method"], "deterministic_rules"
        )
        self.assertEqual(diagnosis["reasoning"]["causal_scope"], "none")

    def test_assessment_only_reports_observable_failure_for_explicit_failure(self):
        run = {
            "skill_run_id": "run-assessment-failure",
            "status": "failed",
            "session_completeness": "complete",
            "activation_mode": "explicit_tool",
            "stage_summary": stage_summary(
                discovery="unsupported",
                execution="failed",
            ),
            "events": [
                {
                    "stage": "execution",
                    "event_type": "tool.failed",
                    "status": "failed",
                    "evidence_grade": "observed",
                    "summary": "Command exited with status 1",
                    "basis": "Observed tool result",
                },
                {
                    "stage": "outcome",
                    "event_type": "outcome.verified",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Test failed",
                    "basis": "Deterministic test",
                },
            ],
        }

        assessment = assess_skill_run(run)

        self.assertEqual(assessment["verdict"], "observable_failure")
        self.assertIn("does not establish", assessment["summary"])
        self.assertEqual(
            assessment["diagnosis"]["status"], "explicit_failure"
        )
        self.assertEqual(
            assessment["diagnosis"]["counts"]["confirmed_failures"], 1
        )

    def test_assessment_marks_result_verified_only_for_explicit_verifier(self):
        run = {
            "skill_run_id": "run-assessment-verified",
            "status": "completed",
            "session_completeness": "complete",
            "activation_mode": "explicit_tool",
            "stage_summary": stage_summary(discovery="unsupported"),
            "events": [
                {
                    "stage": "outcome",
                    "event_type": "outcome.reported",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Agent reported completion",
                },
                {
                    "stage": "outcome",
                    "event_type": "outcome.verified",
                    "status": "observed",
                    "evidence_grade": "observed",
                    "summary": "Deterministic test passed",
                },
            ],
        }

        diagnosis = assess_skill_run(run)["diagnosis"]

        self.assertEqual(diagnosis["status"], "result_verified")
        self.assertEqual(diagnosis["counts"]["verification_gaps"], 0)
        self.assertEqual(diagnosis["attention_items"], [])

    def test_missing_verifier_is_a_gap_only_when_skill_expects_one(self):
        run = {
            "skill_run_id": "run-verifier-required",
            "status": "completed",
            "session_completeness": "complete",
            "activation_mode": "explicit_tool",
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
            "behavior_assessment": {
                "status": "not_evaluable",
                "counts": {
                    "total": 1,
                    "checked": 0,
                    "satisfied": 0,
                    "deviations": 0,
                    "expected_not_observed": 0,
                    "not_evaluable": 1,
                },
                "constraints": [],
                "verifier_expected": True,
                "first_deviation_stage": None,
            },
        }

        diagnosis = assess_skill_run(run)["diagnosis"]

        self.assertEqual(diagnosis["status"], "result_unverified")
        self.assertEqual(diagnosis["counts"]["verification_gaps"], 1)


if __name__ == "__main__":
    unittest.main()
