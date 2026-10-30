import unittest

from experiments.real_corpus_audit.compare_reports import _compare


def _report(run_count, signature_count, manifest=None):
    report = {
        "metrics": {
            "run_count": run_count,
            "session_count": 2,
            "skill_definition_count": 1,
            "finding_signatures": [
                {
                    "code": "gap",
                    "stage": "activation",
                    "evidence_grade": "derived",
                    "run_count": signature_count,
                }
            ],
            "owned_event_type_counts": {"tool.started": 4},
            "owned_event_stage_counts": {"execution": 4},
            "owned_event_evidence_grade_counts": {"observed": 4},
        },
        "readiness": {"passed_count": 1},
    }
    if manifest is not None:
        report["dataset_manifest"] = manifest
    return report


class RealCorpusDriftTests(unittest.TestCase):
    def test_detects_aggregate_population_drift(self):
        result = _compare(_report(10, 10), _report(8, 8))

        self.assertEqual(result["count_deltas"]["run_count"]["delta"], -2)
        self.assertEqual(
            result["finding_signature_deltas"][0]["delta"],
            -2,
        )
        self.assertFalse(result["population_stable_on_aggregate_fields"])

    def test_compares_available_manifest_fingerprints(self):
        before = _report(
            10,
            10,
            {
                "snapshot_sha256": "snapshot-a",
                "schema_sha256": "schema",
                "privacy_safe_aggregate_sha256": "aggregate",
            },
        )
        after = _report(
            10,
            10,
            {
                "snapshot_sha256": "snapshot-b",
                "schema_sha256": "schema",
                "privacy_safe_aggregate_sha256": "aggregate",
            },
        )

        comparison = _compare(before, after)["manifest_comparison"]

        self.assertFalse(comparison["exact_snapshot_match"])
        self.assertTrue(comparison["schema_match"])
        self.assertTrue(comparison["privacy_safe_aggregate_match"])

    def test_exposes_event_drift_when_run_population_is_stable(self):
        before = _report(10, 10)
        after = _report(10, 10)
        after["metrics"]["owned_event_type_counts"]["tool.started"] = 5
        after["metrics"]["owned_event_stage_counts"]["execution"] = 5
        after["metrics"]["owned_event_evidence_grade_counts"]["observed"] = 5

        comparison = _compare(before, after)

        self.assertTrue(comparison["selected_run_population_fields_stable"])
        self.assertEqual(
            comparison["owned_event_counter_deltas"][
                "owned_event_type_counts"
            ][0]["delta"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
