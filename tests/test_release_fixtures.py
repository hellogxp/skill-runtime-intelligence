import tempfile
import unittest
from pathlib import Path

from scripts.fetch_release_fixtures import _download, _entry


ROOT = Path(__file__).resolve().parents[1]
WHEEL_MANIFEST = (
    ROOT
    / "experiments"
    / "product_lifecycle"
    / "release_wheel_manifest_v0.1.json"
)


class ReleaseFixtureTests(unittest.TestCase):
    def test_manifest_has_unique_digest_pinned_release_entry(self):
        entry = _entry(WHEEL_MANIFEST, "0.1.0")
        self.assertEqual(entry["version"], "0.1.0")
        self.assertEqual(len(entry["sha256"]), 64)
        self.assertGreater(entry["bytes"], 0)

    def test_unknown_version_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "no unique entry"):
            _entry(WHEEL_MANIFEST, "9.9.9")

    def test_download_rejects_non_github_origin_before_network_access(self):
        entry = {
            "url": "https://example.com/fixture.whl",
            "filename": "fixture.whl",
            "bytes": 1,
            "sha256": "0" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "unsupported fixture origin"):
                _download(entry, Path(temporary))

    def test_download_rejects_unsafe_filename(self):
        entry = {
            "url": "https://github.com/example/release/fixture.whl",
            "filename": "../fixture.whl",
            "bytes": 1,
            "sha256": "0" * 64,
        }
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "unsafe fixture filename"):
                _download(entry, Path(temporary))


if __name__ == "__main__":
    unittest.main()
