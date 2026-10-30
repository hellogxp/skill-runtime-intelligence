import unittest

from experiments.product_lifecycle.native_launch_phase_readiness_audit import (
    audit_reports,
)


def _report():
    rows = []
    for block in range(8):
        cells = (
            ("direct_copy", "original_linker"),
            ("direct_copy", "adhoc_resigned"),
            ("atomic_replace", "original_linker"),
            ("atomic_replace", "adhoc_resigned"),
        )
        order = cells[block % 4 :] + cells[: block % 4]
        for position, (placement, signature) in enumerate(order):
            rows.append(
                {
                    "block": block,
                    "position": position,
                    "placement": placement,
                    "provenance": "preserved",
                    "signature": signature,
                    "factor_setup": {"passed": True},
                }
            )
    return {
        "experiment": {
            "name": "native-sender-placement-signature-factorial"
        },
        "environment": {
            "platform": "Darwin-test",
            "machine": "arm64",
        },
        "trials": rows,
        "gate": {"passed": True},
    }


class NativeLaunchPhaseReadinessAuditTests(unittest.TestCase):
    def test_descriptive_ready_but_confirmatory_not_ready(self):
        reports = [_report(), _report(), _report()]
        summary = {
            "metrics": {
                "per_run_cell_boundaries": {
                    "cell": {"p50_values_ms": [10, 20, 30]}
                },
                "factor_run_boundaries": {
                    "placement": {
                        "direction_consistent_across_run_p50s": False
                    },
                    "signature": {
                        "direction_consistent_across_run_p50s": False
                    },
                },
            }
        }

        result = audit_reports(reports, summary)

        self.assertTrue(result["gate"]["passed"])
        self.assertTrue(result["readiness"]["descriptive_analysis_ready"])
        self.assertFalse(result["readiness"]["confirmatory_effect_ready"])
        self.assertEqual(result["metrics"]["criteria_passed"], 5)


if __name__ == "__main__":
    unittest.main()
