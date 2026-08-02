import sqlite3
import unittest

from experiments.cross_agent.experiment_evidence_schema_migration_benchmark import (
    _insert_task,
    _migrate,
)


class ExperimentEvidenceSchemaMigrationTests(unittest.TestCase):
    def setUp(self):
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute(
            "CREATE TABLE sessions(session_id TEXT PRIMARY KEY)"
        )

    def tearDown(self):
        self.connection.close()

    def test_migration_is_additive_and_task_import_is_idempotent(self):
        _migrate(self.connection)
        task_key = "sri_task_" + "a" * 32
        self.assertEqual(
            _insert_task(self.connection, task_key, "v1"), "inserted"
        )
        self.assertEqual(
            _insert_task(self.connection, task_key, "v1"), "idempotent"
        )
        self.assertIsNotNone(
            self.connection.execute(
                "SELECT name FROM sqlite_master WHERE name = 'sessions'"
            ).fetchone()
        )

    def test_invalid_task_key_fails_constraint(self):
        _migrate(self.connection)
        with self.assertRaises(sqlite3.IntegrityError):
            _insert_task(self.connection, "invalid", "v1")

    def test_failed_migration_transaction_leaves_no_experimental_tables(self):
        self.connection.execute("BEGIN")
        with self.assertRaises(sqlite3.IntegrityError):
            _migrate(self.connection)
            _insert_task(self.connection, "invalid", "v1")
        self.connection.rollback()
        tables = {
            row[0]
            for row in self.connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        self.assertNotIn("experimental_tasks", tables)
        self.assertNotIn("experimental_outcomes", tables)


if __name__ == "__main__":
    unittest.main()
