import unittest
from pathlib import Path
import sqlite3
import tempfile

from experiments.real_corpus_audit.provenance_reindex_benchmark import (
    _boundary_change_count,
    _checkpoint_converged,
    _checkpoint_matches_source,
    _checkpoint_state,
    _delta,
)


class ProvenanceReindexBenchmarkTests(unittest.TestCase):
    def test_delta_is_grouped_by_provenance_and_omits_zeroes(self):
        before = {
            "official_hook": {"sessions": 1, "events": 2},
            "transcript_fallback": {"sessions": 2, "events": 4},
        }
        after = {
            "official_hook": {"sessions": 1, "events": 2},
            "transcript_fallback": {"sessions": 2, "events": 5},
        }

        result = _delta(before, after)

        self.assertEqual(
            result,
            {"transcript_fallback": {"events": 1}},
        )

    def test_boundary_change_counts_modify_add_and_remove(self):
        before = {"a": 1, "b": 2}
        after = {"a": 2, "c": 3}

        self.assertEqual(_boundary_change_count(before, after), 3)

    def test_checkpoint_requires_completed_zero_late_cut(self):
        self.assertTrue(
            _checkpoint_converged(
                {
                    "status": "completed",
                    "failed_source_count": 0,
                    "late_arrival_count": 0,
                    "end_revision": 12,
                }
            )
        )
        self.assertFalse(
            _checkpoint_converged(
                {
                    "status": "running",
                    "failed_source_count": 0,
                    "late_arrival_count": 0,
                    "end_revision": None,
                }
            )
        )

    def test_checkpoint_state_only_emits_aggregate_allowlist(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE runtime_state "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO runtime_state(key, value) VALUES (?, ?)",
                (
                    "collection.codex.epoch",
                    '{"status":"completed","epoch":2,'
                    '"failed_source_count":0,"late_arrival_count":0,'
                    '"end_revision":12,"source_watermark_sha256":"secret"}',
                ),
            )
            connection.commit()
            connection.close()

            state = _checkpoint_state(database)

        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["epoch"], 2)
        self.assertNotIn("source_watermark_sha256", state)

    def test_checkpoint_source_match_is_boolean_and_hash_stays_private(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            source = Path(directory) / "session.jsonl"
            mtimes = {source: 123}
            from skill_runtime_intelligence.indexer import _source_watermark

            connection = sqlite3.connect(database)
            connection.execute(
                "CREATE TABLE runtime_state "
                "(key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            connection.execute(
                "INSERT INTO runtime_state(key, value) VALUES (?, ?)",
                (
                    "collection.codex.epoch",
                    '{"source_watermark_sha256":"'
                    + _source_watermark(mtimes)
                    + '"}',
                ),
            )
            connection.commit()
            connection.close()

            self.assertTrue(_checkpoint_matches_source(database, mtimes))
            self.assertFalse(
                _checkpoint_matches_source(database, {source: 124})
            )


if __name__ == "__main__":
    unittest.main()
