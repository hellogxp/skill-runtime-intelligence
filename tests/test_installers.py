import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerContractTests(unittest.TestCase):
    def test_public_installer_starts_by_default(self):
        path = ROOT / "scripts/install.sh"
        syntax = subprocess.run(
            ["sh", "-n", str(path)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, syntax.returncode, syntax.stderr)
        source = path.read_text(encoding="utf-8")
        self.assertIn("start_after_install=1", source)
        self.assertIn("--no-start", source)


if __name__ == "__main__":
    unittest.main()
