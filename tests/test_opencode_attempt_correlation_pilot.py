import json
import tempfile
import unittest
from pathlib import Path

from experiments.live_agent.run_opencode_attempt_correlation_pilot import (
    PLUGIN,
    _files_contain,
    _read_evidence,
)


class OpenCodeAttemptCorrelationPilotTests(unittest.TestCase):
    def test_plugin_removes_raw_environment_before_tools(self):
        source = PLUGIN.read_text(encoding="utf-8")
        self.assertIn("delete process.env.SRI_ATTEMPT_CORRELATION_TOKEN", source)
        self.assertIn('"tool.execute.before"', source)

    def test_evidence_reader_ignores_malformed_lines(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "evidence.jsonl"
            path.write_text(
                json.dumps({"event_type": "session.created"}) + "\ninvalid\n",
                encoding="utf-8",
            )
            self.assertEqual(len(_read_evidence(path)), 1)

    def test_raw_token_scanner(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "safe.txt"
            path.write_text("digest only", encoding="utf-8")
            self.assertFalse(_files_contain(Path(root), "sri_corr_secret"))
            path.write_text("sri_corr_secret", encoding="utf-8")
            self.assertTrue(_files_contain(Path(root), "sri_corr_secret"))


if __name__ == "__main__":
    unittest.main()
