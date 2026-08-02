import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release.py"


class ReleaseMetadataTests(unittest.TestCase):
    def test_repository_release_metadata_is_consistent(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--tag", "v0.3.0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_mismatched_tag_fails_closed(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--tag", "v9.9.9"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("expected v0.3.0", result.stderr)

    def test_release_check_validates_links_and_screenshot_format(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--tag", "v0.3.0"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("local_links=valid", result.stdout)
        self.assertIn("screenshot=valid_png", result.stdout)


if __name__ == "__main__":
    unittest.main()
