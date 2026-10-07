import os
import socket
import sys
import tempfile
import unittest
import json
from argparse import Namespace
from pathlib import Path
from unittest import mock

from skill_runtime_intelligence import cli
from skill_runtime_intelligence import runtime_manager
from skill_runtime_intelligence.config import default_config, load_config, save_config
from skill_runtime_intelligence.runtime_manager import (
    RUNTIME_STATE_VERSION,
    restart_runtime,
    runtime_status,
    start_runtime,
    stop_runtime,
)


class RuntimeLifecycleTests(unittest.TestCase):
    def test_transcript_watcher_runs_as_a_supervised_child_process(self):
        args = Namespace(
            database=Path("/tmp/runtime.db"),
            codex_sessions=Path("/tmp/sessions"),
            project=Path("/tmp/project"),
            config=Path("/tmp/config.json"),
            watch_interval=2.0,
            skill_root=[Path("/tmp/skills")],
            exclude=[Path("/tmp/excluded")],
        )
        with mock.patch.object(
            cli, "_current_runtime_invocation", return_value=["/tmp/skill-runtime.pyz"]
        ), mock.patch.object(cli.os, "getpid", return_value=321):
            command = cli._transcript_watch_command(args, index_first=True)

        self.assertEqual(command[:2], ["/tmp/skill-runtime.pyz", "_collector-watch"])
        self.assertIn("--index-first", command)
        self.assertEqual(command[command.index("--parent-pid") + 1], "321")
        self.assertEqual(command[command.index("--watch-interval") + 1], "2.0")
        self.assertIn(str(Path("/tmp/skills").resolve()), command)
        self.assertIn(str(Path("/tmp/excluded").resolve()), command)

    def test_hidden_watcher_command_requires_parent_identity(self):
        parser = cli.build_parser()
        args = parser.parse_args(
            [
                "_collector-watch",
                "--parent-pid",
                "123",
                "--database",
                "/tmp/runtime.db",
            ]
        )
        self.assertEqual(args.command, "_collector-watch")
        self.assertEqual(args.parent_pid, 123)

    def test_install_remembers_declined_consent_without_reprompting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / "state"
            config = default_config(state)
            config["hooks"]["codex"]["consent"] = "declined"
            save_config(config, state / "config.json")
            detected = {"agent": "codex", "detected": True, "installed": False}
            absent = {"detected": False, "installed": False}
            with mock.patch.object(
                cli, "inspect_codex_integration", return_value=detected
            ), mock.patch.object(
                cli, "inspect_claude_integration", return_value={"agent": "claude-code", **absent}
            ), mock.patch.object(
                cli, "inspect_qoder_integration", return_value={"agent": "qoder", **absent}
            ), mock.patch.object(
                cli, "inspect_qoderwork_integration", return_value={"agent": "qoderwork", **absent}
            ), mock.patch.object(
                cli, "inspect_qwenworkcn_integration", return_value={"agent": "qwenworkcn", **absent}
            ), mock.patch.object(
                cli, "inspect_opencode_integration", return_value={"agent": "opencode", **absent}
            ), mock.patch.object(
                cli,
                "install_native_hook_sender",
                return_value={"available": True, "built": False},
            ), mock.patch.object(
                cli,
                "index_local",
                return_value={"sessions": 0, "skill_runs": 0},
            ), mock.patch.object(
                cli, "enable_codex_hooks"
            ) as enable, mock.patch.object(
                cli.sys.stdin, "isatty", return_value=True
            ), mock.patch(
                "builtins.input"
            ) as prompt, mock.patch(
                "builtins.print"
            ):
                cli.main(
                    [
                        "install",
                        "--state-root",
                        str(state),
                        "--project",
                        str(root),
                        "--codex-sessions",
                        str(root / "sessions"),
                    ]
                )
            prompt.assert_not_called()
            enable.assert_not_called()
            self.assertEqual(
                load_config(state / "config.json")["hooks"]["codex"]["consent"],
                "declined",
            )

    def test_unified_setup_enables_detected_hooks_and_persists_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            detected = {
                "agent": "codex",
                "detected": True,
                "installed": False,
            }
            absent = {"detected": False, "installed": False}
            with mock.patch.object(
                cli, "inspect_codex_integration", return_value=detected
            ), mock.patch.object(
                cli, "inspect_claude_integration", return_value={"agent": "claude-code", **absent}
            ), mock.patch.object(
                cli, "inspect_qoder_integration", return_value={"agent": "qoder", **absent}
            ), mock.patch.object(
                cli, "inspect_qoderwork_integration", return_value={"agent": "qoderwork", **absent}
            ), mock.patch.object(
                cli, "inspect_qwenworkcn_integration", return_value={"agent": "qwenworkcn", **absent}
            ), mock.patch.object(
                cli, "inspect_opencode_integration", return_value={"agent": "opencode", **absent}
            ), mock.patch.object(
                cli,
                "enable_codex_hooks",
                return_value={"changed": True, "installed_events": ["PostToolUse"]},
            ) as enable_codex, mock.patch.object(
                cli,
                "build_native_hook_sender",
                return_value={"available": True, "built": False},
            ), mock.patch.object(cli, "_current_executable", return_value="/tmp/skill-runtime"), mock.patch(
                "builtins.print"
            ) as output:
                cli.main(
                    [
                        "setup",
                        "--enable-hooks",
                        "--state-root",
                        str(state),
                    ]
                )

            enable_codex.assert_called_once_with(
                "/tmp/skill-runtime",
                state_root=state,
            )
            config = load_config(state / "config.json")
            self.assertEqual(config["hooks"]["codex"]["consent"], "granted")
            self.assertEqual(config["hooks"]["codex"]["status"], "configured")
            result = json.loads(output.call_args.args[0])
            self.assertEqual(result["action"], "enable")
            self.assertEqual(result["integrations"][0]["agent"], "codex")

    def test_process_command_requests_untruncated_arguments(self):
        completed = mock.Mock(stdout="/usr/bin/python3 -m skill_runtime_intelligence")
        with mock.patch.object(
            runtime_manager.subprocess,
            "run",
            return_value=completed,
        ) as run:
            command = runtime_manager._process_command(123)
        self.assertIn("-m skill_runtime_intelligence", command)
        self.assertEqual(
            run.call_args.args[0],
            ["ps", "-ww", "-p", "123", "-o", "command="],
        )

    def test_uninstall_never_removes_hooks_without_recorded_consent(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            save_config(default_config(state), state / "config.json")
            with mock.patch.object(cli, "stop_runtime", return_value={"changed": False}), \
                 mock.patch.object(cli, "remove_codex_hooks") as remove_codex, \
                 mock.patch.object(cli, "remove_claude_hooks") as remove_claude, \
                 mock.patch("builtins.print") as output:
                cli.main(
                    [
                        "uninstall",
                        "--state-root",
                        str(state),
                        "--keep-data",
                        "--yes",
                    ]
                )
            remove_codex.assert_not_called()
            remove_claude.assert_not_called()
            result = json.loads(output.call_args.args[0])
            self.assertTrue(all(item["skipped"] for item in result["hooks"]))
            self.assertTrue(
                all(
                    item["reason"] == "not_owned_by_this_installation"
                    for item in result["hooks"]
                )
            )

    def test_uninstall_only_removes_hooks_owned_by_this_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory) / "state"
            config = default_config(state)
            config["hooks"]["codex"]["consent"] = "granted"
            save_config(config, state / "config.json")
            with mock.patch.object(cli, "stop_runtime", return_value={"changed": False}), \
                 mock.patch.object(
                     cli,
                     "remove_codex_hooks",
                     return_value={"changed": True, "removed_events": ["PostToolUse"]},
                 ) as remove_codex, \
                 mock.patch.object(cli, "remove_claude_hooks") as remove_claude, \
                 mock.patch("builtins.print"):
                cli.main(
                    [
                        "uninstall",
                        "--state-root",
                        str(state),
                        "--keep-data",
                        "--yes",
                    ]
                )
            remove_codex.assert_called_once_with(state_root=state)
            remove_claude.assert_not_called()

    def test_tampered_marker_cannot_claim_an_unrelated_process(self):
        record = {
            "version": RUNTIME_STATE_VERSION,
            "pid": 123,
            "marker": "sleep",
        }
        with mock.patch.object(
            runtime_manager, "_process_alive", return_value=True
        ), mock.patch.object(
            runtime_manager,
            "_process_command",
            return_value="/usr/bin/sleep 60",
        ):
            self.assertFalse(runtime_manager._managed_process(record))

    def test_status_recognizes_product_health_without_claiming_process_ownership(self):
        with mock.patch.object(
            runtime_manager, "_read_record", return_value={}
        ), mock.patch.object(
            runtime_manager,
            "fetch_health",
            return_value={
                "ok": True,
                "product": "skill-runtime-intelligence",
                "version": "0.1.6",
            },
        ):
            status = runtime_status(port=4317)
        self.assertTrue(status["running"])
        self.assertTrue(status["collector_healthy"])
        self.assertFalse(status["managed"])
        self.assertEqual(status["management_mode"], "external")
        self.assertIsNone(status["pid"])

    def test_status_never_claims_an_unidentified_service(self):
        with mock.patch.object(
            runtime_manager, "_read_record", return_value={}
        ), mock.patch.object(
            runtime_manager,
            "fetch_health",
            return_value={"ok": True},
        ):
            status = runtime_status(port=4317)
        self.assertFalse(status["running"])
        self.assertEqual(status["management_mode"], "none")

    def test_restart_preserves_the_verified_managed_command(self):
        command = [
            "/tmp/skill-runtime.pyz",
            "start",
            "--foreground",
            "--database",
            "/tmp/custom.db",
            "--project",
            "/tmp/custom-project",
        ]
        record = {
            "version": RUNTIME_STATE_VERSION,
            "pid": 123,
            "marker": "skill-runtime-intelligence",
            "command": command,
            "host": "127.0.0.1",
            "port": 4777,
        }
        with mock.patch.object(
            runtime_manager, "_read_record", return_value=record
        ), mock.patch.object(
            runtime_manager, "_managed_process", return_value=True
        ), mock.patch.object(
            runtime_manager, "stop_runtime"
        ) as stop, mock.patch.object(
            runtime_manager,
            "start_runtime",
            return_value={"running": True},
        ) as start:
            result = restart_runtime(port=4317)
        self.assertTrue(result["running"])
        stop.assert_called_once_with(None, "127.0.0.1", 4777)
        self.assertEqual(start.call_args.args[0], command)
        self.assertEqual(start.call_args.kwargs["port"], 4777)

    def test_module_runtime_accepts_interpreter_alias_but_not_argument_drift(self):
        record = {
            "version": RUNTIME_STATE_VERSION,
            "pid": 123,
            "marker": "skill-runtime-intelligence",
            "command": [
                "/toolcache/bin/python3",
                "-m",
                "skill_runtime_intelligence",
                "start",
                "--foreground",
                "--database",
                "/tmp/runtime.db",
            ],
        }
        with mock.patch.object(
            runtime_manager, "_process_alive", return_value=True
        ), mock.patch.object(
            runtime_manager,
            "_process_command",
            return_value=(
                "/Library/Frameworks/Python.framework/Versions/3.13/"
                "Resources/Python.app/Contents/MacOS/Python "
                "-m skill_runtime_intelligence start --foreground "
                "--database /tmp/runtime.db"
            ),
        ):
            self.assertTrue(runtime_manager._managed_process(record))
        with mock.patch.object(
            runtime_manager, "_process_alive", return_value=True
        ), mock.patch.object(
            runtime_manager,
            "_process_command",
            return_value=(
                "/usr/bin/python3 -m skill_runtime_intelligence start "
                "--foreground --database /tmp/unrelated.db"
            ),
        ):
            self.assertFalse(runtime_manager._managed_process(record))

    def test_zipapp_launcher_is_verified_from_recorded_command(self):
        record = {
            "version": RUNTIME_STATE_VERSION,
            "pid": 123,
            "marker": "skill-runtime-intelligence",
            "command": [
                "/tmp/skill-runtime.pyz",
                "start",
                "--foreground",
            ],
        }
        with mock.patch.object(
            runtime_manager, "_process_alive", return_value=True
        ), mock.patch.object(
            runtime_manager,
            "_process_command",
            return_value=(
                "/usr/bin/python3 /tmp/skill-runtime.pyz "
                "start --foreground --port 4317"
            ),
        ):
            self.assertTrue(runtime_manager._managed_process(record))

    def test_managed_runtime_starts_reports_health_and_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sessions = root / "sessions"
            sessions.mkdir()
            project = root / "project"
            project.mkdir()
            state = root / "state"
            database = state / "data" / "panorama.db"
            config = state / "config.json"
            event_queue = state / "queue" / "events.jsonl"
            hook_socket = state / "run" / "hook.sock"
            probe = socket.socket()
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
            probe.close()
            command = [
                sys.executable,
                "-m",
                "skill_runtime_intelligence",
                "start",
                "--foreground",
                "--no-open",
                "--database",
                str(database),
                "--config",
                str(config),
                "--codex-sessions",
                str(sessions),
                "--project",
                str(project),
                "--event-queue",
                str(event_queue),
                "--hook-socket",
                str(hook_socket),
                "--port",
                str(port),
            ]
            source_root = str(Path(__file__).resolve().parents[1] / "src")
            environment = {"PYTHONPATH": source_root, "SKILL_RUNTIME_HOME": str(state)}
            with mock.patch.dict(os.environ, environment, clear=False):
                # Fresh macOS runners can spend tens of seconds validating the
                # first background executable. Exercise the production startup
                # budget instead of introducing a shorter test-only timeout.
                started = start_runtime(command, state_root=state, port=port)
                try:
                    self.assertTrue(started["running"])
                    self.assertTrue(runtime_status(state, port=port)["collector_healthy"])
                finally:
                    stopped = stop_runtime(state, port=port)
            self.assertTrue(stopped["changed"])
            self.assertFalse(runtime_status(state, port=port)["running"])
