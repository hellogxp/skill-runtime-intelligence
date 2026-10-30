import tempfile
import unittest
from pathlib import Path

from experiments.privacy_safe_host_identity import scoped_host_alias


class PrivacySafeHostIdentityTests(unittest.TestCase):
    def test_alias_is_stable_within_scope_and_distinct_across_scopes(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = Path(directory) / "host.secret"
            first = scoped_host_alias(identity, "experiment-a")
            repeated = scoped_host_alias(identity, "experiment-a")
            other = scoped_host_alias(identity, "experiment-b")

            self.assertEqual(first["host_alias"], repeated["host_alias"])
            self.assertNotEqual(first["host_alias"], other["host_alias"])
            self.assertEqual(identity.stat().st_mode & 0o777, 0o600)

    def test_corrupt_identity_fails_without_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = Path(directory) / "host.secret"
            identity.write_text("invalid\n", encoding="ascii")
            identity.chmod(0o600)

            with self.assertRaises(ValueError):
                scoped_host_alias(identity, "experiment-a")

            self.assertEqual(identity.read_text(encoding="ascii"), "invalid\n")

    def test_symlink_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "real.secret"
            scoped_host_alias(real, "experiment-a")
            link = root / "link.secret"
            link.symlink_to(real)

            with self.assertRaises(ValueError):
                scoped_host_alias(link, "experiment-a")


if __name__ == "__main__":
    unittest.main()
