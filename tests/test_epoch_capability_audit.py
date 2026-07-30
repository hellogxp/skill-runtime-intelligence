import sqlite3
import unittest

from experiments.real_corpus_audit.epoch_capability_audit import (
    _audit_connection,
)


class EpochCapabilityAuditTests(unittest.TestCase):
    def test_reports_aggregate_capabilities_without_raw_keys(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE runtime_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO runtime_state VALUES ('revision', '7', 'now');
            INSERT INTO runtime_state VALUES (
                'export.otlp.private-destination.status', '{}', 'now'
            );
            CREATE TABLE imports (
                source_digest TEXT,
                imported_at TEXT
            );
            CREATE TABLE sessions (
                last_event_at TEXT
            );
            """
        )

        metrics = _audit_connection(connection)
        connection.close()

        self.assertEqual(metrics["current_global_revision"], 7)
        self.assertEqual(metrics["runtime_state_key_count"], 2)
        self.assertEqual(
            metrics["runtime_state_key_category_counts"],
            {"global_revision": 1, "otlp_export": 1},
        )
        self.assertEqual(metrics["available_capability_count"], 3)
        self.assertFalse(metrics["freeze_checkpoint_available"])
        self.assertNotIn("private-destination", str(metrics))

    def test_recognizes_complete_epoch_payload_without_emitting_it(self):
        connection = sqlite3.connect(":memory:")
        connection.executescript(
            """
            CREATE TABLE runtime_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO runtime_state VALUES ('revision', '8', 'now');
            CREATE TABLE imports (
                source_digest TEXT,
                imported_at TEXT
            );
            CREATE TABLE sessions (
                last_event_at TEXT
            );
            """
        )
        connection.execute(
            "INSERT INTO runtime_state VALUES (?, ?, ?)",
            (
                "collection.codex.epoch",
                (
                    '{"epoch":2,"status":"completed",'
                    '"source_watermark_sha256":"private-watermark",'
                    '"late_arrival_count":1}'
                ),
                "now",
            ),
        )

        metrics = _audit_connection(connection)
        connection.close()

        self.assertEqual(metrics["available_capability_count"], 7)
        self.assertTrue(metrics["freeze_checkpoint_available"])
        self.assertNotIn("private-watermark", str(metrics))


if __name__ == "__main__":
    unittest.main()
