import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.indexer import (
    _eligible_source_mtimes,
    _index_changed_batch,
    _source_watermark,
)
from skill_runtime_intelligence.storage import Storage


class CollectionEpochTests(unittest.TestCase):
    def test_epoch_records_progress_without_source_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "panorama.db")
            try:
                started = storage.begin_collection_epoch(
                    "codex",
                    source_count=5,
                    changed_source_count=2,
                    removed_source_count=1,
                    source_watermark_sha256="a" * 64,
                )
                self.assertEqual(started["epoch"], 1)
                self.assertEqual(started["status"], "running")
                self.assertEqual(started["removed_source_count"], 1)

                completed = storage.complete_collection_epoch(
                    "codex",
                    started["epoch"],
                    processed_source_count=1,
                    failed_source_count=1,
                    late_arrival_count=1,
                )
                self.assertEqual(completed["status"], "completed")
                self.assertEqual(completed["processed_source_count"], 1)
                self.assertEqual(completed["failed_source_count"], 1)
                self.assertEqual(completed["late_arrival_count"], 1)
                self.assertNotIn(directory, str(completed))

                second = storage.begin_collection_epoch(
                    "codex",
                    source_count=5,
                    changed_source_count=1,
                    source_watermark_sha256="b" * 64,
                )
                self.assertEqual(second["epoch"], 2)
            finally:
                storage.close()

    def test_epoch_rejects_invalid_transition(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Storage(Path(directory) / "panorama.db")
            try:
                started = storage.begin_collection_epoch(
                    "codex",
                    source_count=1,
                    changed_source_count=1,
                    source_watermark_sha256="a" * 64,
                )
                with self.assertRaises(RuntimeError):
                    storage.complete_collection_epoch(
                        "codex",
                        started["epoch"] + 1,
                        processed_source_count=0,
                        failed_source_count=1,
                        late_arrival_count=0,
                    )
            finally:
                storage.close()

    def test_source_watermark_is_order_stable_and_change_sensitive(self):
        left = {Path("/a"): 1, Path("/b"): 2}
        right = {Path("/b"): 2, Path("/a"): 1}
        changed = {Path("/a"): 1, Path("/b"): 3}

        self.assertEqual(_source_watermark(left), _source_watermark(right))
        self.assertNotEqual(_source_watermark(left), _source_watermark(changed))

    def test_changed_batch_writes_completed_epoch(self):
        class _Adapter:
            def parse(self, source_path, skills):
                return (
                    {
                        "session_id": "fixture-session",
                        "adapter": "codex",
                        "adapter_version": "fixture",
                        "source_path": str(source_path),
                        "source_format_version": "fixture",
                        "title": "",
                        "cwd": "",
                        "model": "",
                        "agent_version": "",
                        "started_at": None,
                        "ended_at": None,
                        "duration_ms": None,
                        "status": "incomplete",
                        "completeness": "partial",
                        "event_count": 0,
                    },
                    [],
                    [],
                    [],
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "session.jsonl"
            source.write_text("{}\n", encoding="utf-8")
            database = root / "panorama.db"
            mtime = source.stat().st_mtime_ns

            completed = _index_changed_batch(
                database,
                _Adapter(),
                [],
                [source],
                {source: mtime},
            )

            self.assertEqual(completed["status"], "completed")
            self.assertEqual(completed["processed_source_count"], 1)
            self.assertEqual(completed["late_arrival_count"], 0)
            storage = Storage(database)
            try:
                self.assertEqual(
                    storage.collection_epoch("codex")["status"],
                    "completed",
                )
            finally:
                storage.close()

    def test_changed_batch_counts_new_source_inside_epoch(self):
        class _Adapter:
            def __init__(self, root):
                self.root = root

            def session_files(self):
                return list(self.root.glob("*.jsonl"))

            def peek_cwd(self, source_path):
                return None

            def parse(self, source_path, skills):
                (self.root / "late.jsonl").write_text(
                    "{}\n",
                    encoding="utf-8",
                )
                return (
                    {
                        "session_id": "fixture-session",
                        "adapter": "codex",
                        "adapter_version": "fixture",
                        "source_path": str(source_path),
                        "source_format_version": "fixture",
                        "title": "",
                        "cwd": "",
                        "model": "",
                        "agent_version": "",
                        "started_at": None,
                        "ended_at": None,
                        "duration_ms": None,
                        "status": "incomplete",
                        "completeness": "partial",
                        "event_count": 0,
                    },
                    [],
                    [],
                    [],
                )

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "session.jsonl"
            source.write_text("{}\n", encoding="utf-8")
            adapter = _Adapter(root)
            boundary = _eligible_source_mtimes(adapter, [])

            completed = _index_changed_batch(
                root / "panorama.db",
                adapter,
                [],
                [source],
                boundary,
                source_boundary_probe=lambda: _eligible_source_mtimes(
                    adapter,
                    [],
                ),
            )

        self.assertEqual(completed["late_arrival_count"], 1)


if __name__ == "__main__":
    unittest.main()
