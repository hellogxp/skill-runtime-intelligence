import sqlite3
import unittest

from experiments.cross_agent.experiment_evidence_import_benchmark import (
    _import_row,
    _prepare_isolated_database,
)


class ExperimentEvidenceImportBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        _prepare_isolated_database(self.connection)
        self.index = {
            "a" * 64: [{"session_id": "private-session", "adapter": "codex"}]
        }
        self.row = {
            "adapter": "codex",
            "source_session_sha256": "a" * 64,
            "report_sha256": "b" * 64,
            "outcome": "verified_success",
        }

    def tearDown(self):
        self.connection.close()

    def test_import_is_idempotent(self):
        self.assertEqual(
            _import_row(self.connection, self.row, self.index, "task", "verifier"),
            "inserted",
        )
        self.assertEqual(
            _import_row(self.connection, self.row, self.index, "task", "verifier"),
            "idempotent",
        )

    def test_wrong_or_ambiguous_link_fails_closed(self):
        with self.assertRaises(ValueError):
            _import_row(
                self.connection,
                dict(self.row, source_session_sha256="0" * 64),
                self.index,
                "task",
                "verifier",
            )
        with self.assertRaises(ValueError):
            _import_row(
                self.connection,
                dict(self.row, adapter="qoder"),
                self.index,
                "task",
                "verifier",
            )

    def test_conflicting_outcome_is_rejected(self):
        _import_row(self.connection, self.row, self.index, "task", "verifier")
        with self.assertRaises(ValueError):
            _import_row(
                self.connection,
                dict(self.row, outcome="verified_failure"),
                self.index,
                "task",
                "verifier",
            )


if __name__ == "__main__":
    unittest.main()
