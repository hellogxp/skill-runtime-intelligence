import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from experiments.real_corpus_audit.run_benchmark import (
    _aggregate,
    _canonical_sha256,
    _consistent_snapshot,
    _contains_forbidden_row_data,
    _snapshot_manifest,
)


class _FakeStorage:
    def list_skill_runs(self, limit=100_000):
        return [
            {
                "skill_run_id": "private-run",
                "session_id": "private-session",
                "skill_id": "private-skill",
                "status": "completed",
                "adapter": "codex",
                "evidence_grade": "derived",
                "activation_mode": "inferred",
            }
        ]

    def get_skill_run(self, skill_run_id):
        return {
            "session_completeness": "complete",
            "stage_summary": [
                {"stage": "request", "status": "observed"},
                {"stage": "activation", "status": "not_observed"},
                {"stage": "outcome", "status": "observed"},
            ],
            "findings": [
                {
                    "code": "lifecycle_evidence_gap",
                    "stage": "activation",
                    "evidence_grade": "derived",
                    "summary": "private finding summary",
                }
            ],
            "events": [
                {
                    "event_id": "private-event",
                    "event_type": "outcome.reported",
                    "stage": "outcome",
                    "evidence_grade": "observed",
                    "status": "reported",
                    "payload": {"secret": "private payload"},
                    "context_only": 0,
                }
            ],
        }


class RealCorpusAuditTests(unittest.TestCase):
    def test_aggregate_emits_counts_without_private_values(self):
        metrics, readiness = _aggregate(_FakeStorage())
        serialized = json.dumps(
            {"metrics": metrics, "readiness": readiness},
            sort_keys=True,
        )

        self.assertEqual(metrics["run_count"], 1)
        self.assertEqual(metrics["adapter_counts"], {"codex": 1})
        self.assertEqual(metrics["finding_occurrence_count"], 1)
        self.assertEqual(
            metrics["dominant_finding_signature_run_coverage"],
            1.0,
        )
        self.assertEqual(
            len(metrics["systematic_finding_signatures_at_80pct"]),
            1,
        )
        self.assertNotIn("private-", serialized)
        self.assertFalse(readiness["corpus_ready_for_confirmatory_evaluation"])

    def test_privacy_audit_rejects_row_level_fields(self):
        self.assertFalse(
            _contains_forbidden_row_data(
                {"metrics": {"adapter_counts": {"codex": 1}}}
            )
        )
        self.assertTrue(
            _contains_forbidden_row_data(
                {"metrics": {"skill_run_id": "private-run"}}
            )
        )

    def test_consistent_snapshot_does_not_change_source_content(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.db"
            connection = sqlite3.connect(source)
            connection.execute("CREATE TABLE marker (value TEXT)")
            connection.execute("INSERT INTO marker VALUES ('unchanged')")
            connection.commit()
            connection.close()
            before = source.read_bytes()

            snapshot, attempts = _consistent_snapshot(source)
            try:
                copied = sqlite3.connect(snapshot)
                value = copied.execute("SELECT value FROM marker").fetchone()[0]
                copied.close()
            finally:
                snapshot.unlink(missing_ok=True)

            self.assertEqual(value, "unchanged")
            self.assertGreaterEqual(attempts, 1)
            self.assertEqual(source.read_bytes(), before)

    def test_canonical_hash_is_independent_of_dictionary_key_order(self):
        self.assertEqual(
            _canonical_sha256({"a": 1, "b": 2}),
            _canonical_sha256({"b": 2, "a": 1}),
        )

    def test_snapshot_manifest_has_integrity_and_no_row_values(self):
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot.db"
            connection = sqlite3.connect(snapshot)
            connection.execute("CREATE TABLE marker (value TEXT)")
            connection.execute("INSERT INTO marker VALUES ('private-marker')")
            connection.commit()
            connection.close()

            manifest = _snapshot_manifest(
                snapshot,
                {"run_count": 1},
                {"passed_count": 1},
            )
            serialized = json.dumps(manifest, sort_keys=True)

            self.assertEqual(manifest["integrity_check"], "ok")
            self.assertEqual(len(manifest["snapshot_sha256"]), 64)
            self.assertEqual(len(manifest["schema_sha256"]), 64)
            self.assertEqual(
                len(manifest["privacy_safe_aggregate_sha256"]),
                64,
            )
            self.assertNotIn("private-marker", serialized)
            self.assertFalse(_contains_forbidden_row_data(manifest))


if __name__ == "__main__":
    unittest.main()
