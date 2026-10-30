import unittest

from skill_runtime_intelligence.redaction import REDACTED, redact, redact_text


class RedactionTests(unittest.TestCase):
    def test_redacts_common_tokens(self):
        token = "github_pat_" + ("a" * 48)
        self.assertNotIn(token, redact_text(f"use {token} now"))
        self.assertIn(REDACTED, redact_text(f"use {token} now"))

    def test_redacts_sensitive_keys_recursively(self):
        value = {"nested": {"access_token": "do-not-store"}, "safe": "visible"}
        self.assertEqual(redact(value)["nested"]["access_token"], REDACTED)
        self.assertEqual(redact(value)["safe"], "visible")


if __name__ == "__main__":
    unittest.main()
