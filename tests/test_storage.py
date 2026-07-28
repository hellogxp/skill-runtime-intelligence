import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.indexer import index_local
from skill_runtime_intelligence.storage import Storage


class StorageTests(unittest.TestCase):
    def test_empty_index_is_queryable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions"
            skills = root / "skills"
            sessions.mkdir()
            skills.mkdir()
            database = root / "panorama.db"

            result = index_local(database, sessions, [skills])
            self.assertEqual(result["failed"], 0)

            storage = Storage(database)
            try:
                self.assertEqual(storage.list_runs(), [])
                self.assertEqual(storage.list_skills(), [])
            finally:
                storage.close()


if __name__ == "__main__":
    unittest.main()
