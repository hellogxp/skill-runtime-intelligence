import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from experiments.real_corpus_audit.frozen_corpus_reindex_benchmark import (
    _select_historical_sources,
    _source_identity_profile,
    _table_fingerprints,
)
from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.storage import Storage


class FrozenCorpusReindexBenchmarkTests(unittest.TestCase):
    def test_selection_applies_age_file_and_total_byte_limits(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old = 1_000_000_000
            for index, size in enumerate((3, 4, 7)):
                source = root / f"{index}.jsonl"
                source.write_bytes(b"x" * size)
                source.touch()
                source.chmod(0o600)
                os.utime(source, ns=(old + index, old + index))

            selected = _select_historical_sources(
                CodexAdapter(root),
                now_ns=10_000_000_000,
                min_age_seconds=1,
                max_files=3,
                max_file_bytes=5,
                max_total_bytes=6,
            )

        self.assertEqual([value[2] for value in selected], [3])

    def test_identity_profile_detects_divergent_duplicate_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            common = {
                "type": "session_meta",
                "payload": {"session_id": "shared"},
            }
            first = root / "first.jsonl"
            second = root / "second.jsonl"
            first.write_text(
                json.dumps(common) + "\n" + '{"value":1}\n',
                encoding="utf-8",
            )
            second.write_text(
                json.dumps(common) + "\n" + '{"value":2}\n',
                encoding="utf-8",
            )
            os.utime(first, ns=(1, 1))
            os.utime(second, ns=(2, 2))

            profile = _source_identity_profile(CodexAdapter(root))

        self.assertEqual(profile["source_files"], 2)
        self.assertEqual(profile["source_identity_count"], 1)
        self.assertEqual(profile["duplicate_identity_groups"], 1)
        self.assertEqual(profile["divergent_duplicate_groups"], 1)
        self.assertEqual(
            profile["aggregate_unique_line_hashes_absent_from_latest"],
            1,
        )

    def test_fingerprint_ignores_indexed_at_but_detects_graph_change(self):
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory) / "test.db"
            storage = Storage(database)
            storage.close()
            connection = sqlite3.connect(database)
            connection.execute(
                """
                INSERT INTO sessions (
                    session_id, adapter, adapter_version, source_path,
                    source_format_version, title, cwd, model, agent_version,
                    status, completeness, indexed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "session-1",
                    "codex",
                    "1",
                    "/tmp/source",
                    "1",
                    "title",
                    "/tmp",
                    "model",
                    "agent",
                    "completed",
                    "complete",
                    "2026-01-01T00:00:00Z",
                ),
            )
            connection.commit()
            connection.close()
            before = _table_fingerprints(database)

            connection = sqlite3.connect(database)
            connection.execute(
                "UPDATE sessions SET indexed_at = ? WHERE session_id = ?",
                ("2026-02-01T00:00:00Z", "session-1"),
            )
            connection.commit()
            connection.close()
            after_timestamp = _table_fingerprints(database)

            connection = sqlite3.connect(database)
            connection.execute(
                "UPDATE sessions SET status = ? WHERE session_id = ?",
                ("failed", "session-1"),
            )
            connection.commit()
            connection.close()
            after_graph_change = _table_fingerprints(database)

        self.assertEqual(before, after_timestamp)
        self.assertNotEqual(
            before["sessions"],
            after_graph_change["sessions"],
        )


if __name__ == "__main__":
    unittest.main()
