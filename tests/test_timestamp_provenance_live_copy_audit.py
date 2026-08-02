import tempfile
import unittest
from pathlib import Path

from experiments.cross_agent.timestamp_provenance_live_copy_audit import (
    run_audit,
)
from skill_runtime_intelligence.storage import Storage


class TimestampProvenanceLiveCopyAuditTests(unittest.TestCase):
    def test_audit_uses_copy_and_preserves_aggregate_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "panorama.db"
            storage = Storage(database)
            storage.close()

            report = run_audit(database)

        self.assertTrue(report["gate"]["passed"])
        self.assertTrue(report["privacy_audit"]["passed"])
        metrics = report["metrics"]
        self.assertEqual(
            metrics["event_count_before"],
            metrics["event_count_after"],
        )
        self.assertEqual(
            metrics["session_count_before"],
            metrics["session_count_after"],
        )
        self.assertEqual(metrics["provenance_columns_after"], 5)
        self.assertTrue(metrics["quick_check_ok"])


if __name__ == "__main__":
    unittest.main()
