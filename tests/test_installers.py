import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InstallerContractTests(unittest.TestCase):
    def test_public_and_internal_installers_start_by_default(self):
        for relative in ("scripts/install.sh", "scripts/install-internal.sh"):
            path = ROOT / relative
            if not path.exists():
                continue
            syntax = subprocess.run(
                ["sh", "-n", str(path)],
                capture_output=True,
                text=True,
            )
            self.assertEqual(0, syntax.returncode, syntax.stderr)
            source = path.read_text(encoding="utf-8")
            self.assertIn("start_after_install=1", source)
            self.assertIn("--no-start", source)

    def test_internal_installer_uses_tty_for_explicit_hook_consent(self):
        path = ROOT / "scripts/install-internal.sh"
        if not path.exists():
            self.skipTest("internal installer is intentionally not public")
        source = path.read_text(encoding="utf-8")
        self.assertIn('hook_choice="ask"', source)
        self.assertIn("</dev/tty", source)
        self.assertIn("--no-hooks", source)


if __name__ == "__main__":
    unittest.main()
