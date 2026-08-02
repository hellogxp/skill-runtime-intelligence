import subprocess
import sys
import time
import unittest

from experiments.live_agent.run_cross_agent_cli_trials import (
    _command,
    _delta,
    _extract_codex,
    _extract_opencode,
    _extract_qoder,
    _find_expected,
    _run_with_process_group,
    _version,
    _changed_paths,
    _change_summary,
)


class CrossAgentCliTrialTests(unittest.TestCase):
    def setUp(self):
        self.expected = {
            "status": "ok",
            "fixture": "cross-agent-checksum-v1",
            "token": "SRI-test",
        }

    def test_extract_codex(self):
        stdout = "\n".join([
            '{"type":"thread.started","thread_id":"private"}',
            '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"ok\\"}"}}',
            '{"type":"turn.completed","usage":{"input_tokens":3}}',
        ])
        text, session, usage = _extract_codex(stdout)
        self.assertEqual(session, "private")
        self.assertIn('"status":"ok"', text)
        self.assertEqual(usage["input_tokens"], 3)

    def test_extract_opencode(self):
        stdout = "\n".join([
            '{"type":"text","sessionID":"private","part":{"text":"{\\"status\\":\\"ok\\"}"}}',
            '{"type":"step_finish","part":{"tokens":{"input":4}}}',
        ])
        text, session, usage = _extract_opencode(stdout)
        self.assertEqual(session, "private")
        self.assertIn('"status":"ok"', text)
        self.assertEqual(usage["input"], 4)

    def test_extract_qoder_and_find_expected(self):
        stdout = '{"session_id":"private","result":"{\\"status\\":\\"ok\\",\\"fixture\\":\\"cross-agent-checksum-v1\\",\\"token\\":\\"SRI-test\\"}"}'
        text, session, _ = _extract_qoder(stdout)
        self.assertEqual(session, "private")
        self.assertTrue(_find_expected(text, self.expected))

    def test_delta_is_per_agent_and_field(self):
        before = {"codex": {"sessions": 2, "events": 4}}
        after = {"codex": {"sessions": 3, "events": 7}}
        self.assertEqual(
            _delta(before, after),
            {"codex": {"sessions": 1, "events": 3}},
        )

    def test_changed_paths_reports_added_removed_and_modified(self):
        self.assertEqual(
            _changed_paths(
                {"same": "a", "modified": "a", "removed": "a"},
                {"same": "a", "modified": "b", "added": "b"},
            ),
            ["added", "modified", "removed"],
        )

    def test_change_summary_caps_samples_and_groups_roots(self):
        before = {f".opencode/node_modules/file-{index}": "a" for index in range(30)}
        after = {path: "b" for path in before}
        summary = _change_summary(before, after)
        self.assertEqual(summary["workspace_change_count"], 30)
        self.assertEqual(summary["workspace_change_roots"], [".opencode/node_modules"])
        self.assertEqual(len(summary["workspace_change_sample"]), 20)

    def test_qoder_command_uses_explicit_tool_allowlist(self):
        command, stdin = _command(
            "qoder",
            workspace="/tmp/fixture",
            prompt="fixture",
            codex_model="codex-model",
            opencode_model="opencode-model",
            qoder_model="qoder-model",
        )
        self.assertIsNone(stdin)
        self.assertIn("--allowed-tools", command)
        self.assertNotIn("--dangerously-skip-permissions", command)
        self.assertNotIn("--permission-mode", command)

    def test_timeout_reaps_descendants_holding_output_pipes(self):
        started = time.monotonic()
        with self.assertRaises(subprocess.TimeoutExpired):
            _run_with_process_group(
                [
                    sys.executable,
                    "-c",
                    (
                        "import subprocess,sys,time; "
                        "subprocess.Popen([sys.executable,'-c',"
                        "'import time; time.sleep(60)']); time.sleep(60)"
                    ),
                ],
                None,
                0.1,
            )
        self.assertLess(time.monotonic() - started, 5)

    def test_missing_version_command_is_recorded_instead_of_crashing(self):
        self.assertEqual(
            _version("/definitely/missing/sri-agent-cli"),
            "unavailable:FileNotFoundError",
        )


if __name__ == "__main__":
    unittest.main()
