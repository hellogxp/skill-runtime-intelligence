import json
import tempfile
import unittest
from pathlib import Path

from experiments.real_corpus_audit.source_identity_audit import run_audit


class SourceIdentityAuditTests(unittest.TestCase):
    def test_audit_emits_aggregate_multiplicity_without_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, identity in enumerate(("shared", "shared", "solo")):
                source = root / f"{index}.jsonl"
                source.write_text(
                    json.dumps(
                        {
                            "type": "session_meta",
                            "payload": {"id": identity},
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

            report = run_audit(root)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["physical_source_files"], 3)
        self.assertEqual(report["metrics"]["upstream_identity_count"], 2)
        self.assertEqual(report["metrics"]["duplicate_identity_groups"], 1)
        self.assertEqual(
            report["metrics"]["identity_multiplicity_histogram"],
            {"1": 1, "2": 1},
        )
        self.assertNotIn("shared", str(report))
        self.assertNotIn("solo", str(report))


if __name__ == "__main__":
    unittest.main()
