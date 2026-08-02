import sqlite3
import tempfile
import unittest
from pathlib import Path

from experiments.cross_agent.attempt_correlation_contract_benchmark import (
    _bind,
    _schema,
)
from experiments.privacy_safe_attempt_correlation import (
    CORRELATION_SCHEMA,
    attempt_correlation_token,
)


class AttemptCorrelationContractTests(unittest.TestCase):
    def test_token_is_stable_and_domain_separated(self):
        with tempfile.TemporaryDirectory() as root:
            secret = Path(root) / "secret"
            base = {
                "schema_version": CORRELATION_SCHEMA,
                "study_scope": "scope-a",
                "adapter": "qoder",
                "attempt_nonce": "attempt-1",
            }
            first = attempt_correlation_token(secret, base)
            self.assertEqual(first, attempt_correlation_token(secret, base))
            changed = attempt_correlation_token(
                secret, dict(base, adapter="codex")
            )
            self.assertNotEqual(first["token"], changed["token"])

    def test_late_binding_is_idempotent_and_fail_closed(self):
        connection = sqlite3.connect(":memory:")
        connection.execute("PRAGMA foreign_keys = ON")
        _schema(connection)
        token = "sri_corr_" + "a" * 32
        import hashlib
        digest = hashlib.sha256(token.encode("ascii")).hexdigest()
        connection.execute(
            "INSERT INTO attempts VALUES "
            "('attempt-1', 'qoder', ?, 'pending', NULL, 'Experimental')",
            (digest,),
        )
        connection.execute("INSERT INTO sessions VALUES ('session-1', 'qoder')")
        connection.execute("INSERT INTO sessions VALUES ('session-2', 'qoder')")
        self.assertEqual(_bind(connection, token, "qoder", "session-1"), "bound")
        self.assertEqual(
            _bind(connection, token, "qoder", "session-1"), "idempotent"
        )
        with self.assertRaises(ValueError):
            _bind(connection, token, "qoder", "session-2")
        with self.assertRaises(ValueError):
            _bind(connection, token, "codex", "session-1")
        connection.close()


if __name__ == "__main__":
    unittest.main()
