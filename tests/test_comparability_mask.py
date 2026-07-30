import unittest

from skill_runtime_intelligence.comparison import build_comparison


def _run(
    *,
    session_id,
    digest="digest-a",
    status="completed",
    activation_mode="explicit_tool",
    timestamp_origin="agent",
    clock_domain="agent-wall",
    uncertainty=5,
):
    stages = [
        {
            "stage": stage,
            "status": "observed",
            "event_count": 1,
            "capability": "observed",
        }
        for stage in (
            "request",
            "discovery",
            "activation",
            "instructions",
            "resources",
            "execution",
            "artifacts",
            "outcome",
        )
    ]
    return {
        "session_id": session_id,
        "turn_id": "turn-1",
        "correlation_key": session_id,
        "name": "pdf",
        "digest": digest,
        "activation_mode": activation_mode,
        "status": status,
        "stage_summary": stages,
        "adapter_capabilities": {item["stage"]: "observed" for item in stages},
        "events": [
            {
                "event_type": "skill.activated",
                "stage": "activation",
                "occurred_at": "2026-07-30T00:00:00Z",
                "timestamp_origin": timestamp_origin,
                "clock_domain": clock_domain,
                "clock_uncertainty_ms": uncertainty,
            },
            {
                "event_type": "outcome.reported",
                "stage": "outcome",
                "occurred_at": "2026-07-30T00:00:01Z",
                "timestamp_origin": timestamp_origin,
                "clock_domain": clock_domain,
                "clock_uncertainty_ms": uncertainty,
            },
        ],
    }


class ComparabilityMaskTests(unittest.TestCase):
    def test_unaligned_runs_are_side_by_side_but_behavior_is_masked(self):
        comparison = build_comparison(
            _run(session_id="left"),
            _run(session_id="right"),
            task_aligned=False,
        )

        self.assertEqual(comparison["decision"], "not_comparable")
        self.assertEqual(
            comparison["comparability_mask"]["lifecycle"]["status"], "masked"
        )
        self.assertTrue(
            all(stage["changed"] is None for stage in comparison["stages"])
        )
        self.assertFalse(comparison["causal_attribution_allowed"])

    def test_explicit_alignment_enables_behavior_but_time_requires_provenance(self):
        comparison = build_comparison(
            _run(session_id="left"),
            _run(
                session_id="right",
                timestamp_origin="unknown",
                clock_domain="unknown",
                uncertainty=None,
            ),
            task_aligned=True,
        )

        self.assertEqual(
            comparison["comparability_mask"]["lifecycle"]["status"], "comparable"
        )
        self.assertEqual(
            comparison["comparability_mask"]["outcome"]["status"], "comparable"
        )
        self.assertEqual(
            comparison["comparability_mask"]["absolute_time"]["status"], "masked"
        )
        self.assertEqual(comparison["decision"], "partially_comparable")

    def test_skill_version_axis_requires_a_definition_difference(self):
        masked = build_comparison(
            _run(session_id="left"),
            _run(session_id="right"),
            axis="skill_version",
            task_aligned=True,
        )
        comparable = build_comparison(
            _run(session_id="left"),
            _run(session_id="right", digest="digest-b"),
            axis="skill_version",
            task_aligned=True,
        )

        self.assertEqual(
            masked["comparability_mask"]["lifecycle"]["status"], "masked"
        )
        self.assertEqual(
            comparable["comparability_mask"]["lifecycle"]["status"], "comparable"
        )


if __name__ == "__main__":
    unittest.main()
