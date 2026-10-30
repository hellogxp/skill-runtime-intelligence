import sqlite3
import unittest
from pathlib import Path

from experiments.cross_agent.experiment_attempt_failure_import_benchmark import (
    DEFAULT_REPORTS,
    _failure_rows,
    _insert_attempt,
    _migrate_attempts,
)
from experiments.cross_agent.experiment_evidence_schema_migration_benchmark import (
    _insert_task,
    _migrate,
)


class ExperimentAttemptFailureImportTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            "CREATE TABLE sessions(session_id TEXT PRIMARY KEY)"
        )
        _migrate(self.connection)
        _migrate_attempts(self.connection)
        self.task_key = "sri_task_" + "a" * 32
        _insert_task(self.connection, self.task_key, "v1")

    def tearDown(self):
        self.connection.close()

    @unittest.skipUnless(
        all(Path(path).is_file() for path in DEFAULT_REPORTS),
        "requires locally retained live-Agent experiment reports",
    )
    def test_real_reports_preserve_five_failures(self):
        rows, _, _ = _failure_rows(Path(path) for path in DEFAULT_REPORTS)
        self.assertEqual(len(rows), 5)
        self.assertEqual(
            [row["attempt_status"] for row in rows].count("invalid_response"),
            4,
        )
        self.assertEqual(
            [row["attempt_status"] for row in rows].count("execution_error"),
            1,
        )
        self.assertTrue(all(row["source_session_sha256"] is None for row in rows))

    def test_unresolved_attempt_is_idempotent(self):
        row = {
            "attempt_id": "b" * 64,
            "adapter": "qoder",
            "trial_index": 1,
            "attempt_status": "execution_error",
            "verifier_state": "not_run",
            "session_id": None,
            "source_session_sha256": None,
            "resolution_state": "unresolved",
            "unresolved_reason": "source_session_absent",
            "source_report_sha256": "c" * 64,
        }
        self.assertEqual(
            _insert_attempt(self.connection, row, self.task_key), "inserted"
        )
        self.assertEqual(
            _insert_attempt(self.connection, row, self.task_key), "idempotent"
        )

    def test_linked_attempt_requires_session_identity(self):
        row = {
            "attempt_id": "d" * 64,
            "adapter": "qoder",
            "trial_index": 1,
            "attempt_status": "execution_error",
            "verifier_state": "not_run",
            "session_id": None,
            "source_session_sha256": None,
            "resolution_state": "linked",
            "unresolved_reason": None,
            "source_report_sha256": "e" * 64,
        }
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_attempt(self.connection, row, self.task_key)


if __name__ == "__main__":
    unittest.main()
