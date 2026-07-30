import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import socket
import platform
from pathlib import Path

from skill_runtime_intelligence.event_queue import (
    deliver_or_queue,
    drain_event_queue,
)
from skill_runtime_intelligence.hook_adapter import (
    build_claude_hook_envelopes,
    build_codex_hook_envelopes,
    build_opencode_hook_envelopes,
    build_qoder_hook_envelopes,
)
from skill_runtime_intelligence.hook_bridge import (
    SAFE_UNIX_SOCKET_PATH_BYTES,
    HookBridge,
    default_hook_socket,
)
from skill_runtime_intelligence.integrations import (
    MANAGED_CLAUDE_EVENTS,
    MANAGED_CODEX_EVENTS,
    MANAGED_QODER_EVENTS,
    enable_claude_hooks,
    enable_codex_hooks,
    enable_opencode_plugin,
    enable_qoder_hooks,
    inspect_claude_integration,
    inspect_codex_integration,
    inspect_opencode_integration,
    inspect_qoder_integration,
    remove_claude_hooks,
    remove_codex_hooks,
    remove_opencode_plugin,
    remove_qoder_hooks,
)
from skill_runtime_intelligence.native_sender import (
    build_native_hook_sender,
    install_native_hook_sender,
)
from skill_runtime_intelligence.storage import Storage


class HookAdapterTests(unittest.TestCase):
    def test_long_state_root_uses_a_short_stable_socket_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ("nested-" + "x" * 120)
            first = default_hook_socket(root)
            second = default_hook_socket(root)
            self.assertEqual(first, second)
            self.assertLessEqual(
                len(os.fsencode(str(first))),
                SAFE_UNIX_SOCKET_PATH_BYTES,
            )
            self.assertNotEqual(first, root / "run" / "hook.sock")
            bridge = HookBridge(
                Path(directory) / "panorama.db",
                socket_path=first,
            ).start()
            self.assertTrue(first.is_socket())
            bridge.close()
            self.assertFalse(first.exists())
            self.assertFalse(first.parent.exists())

    def test_native_sender_install_prewarms_against_a_missing_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            state_root = (
                Path(directory)
                / ("state-" + ("long-" * 24))
                / ("nested-" + ("path-" * 12))
            )
            result = install_native_hook_sender(
                state_root,
                download_first=False,
            )
            if not result["available"]:
                self.skipTest(result["reason"])
            self.assertTrue(result["prewarm"]["attempted"])
            self.assertTrue(result["prewarm"]["passed"])
            self.assertEqual(result["prewarm"]["exit_code"], 1)
            self.assertEqual(result["prewarm"]["stdout_bytes"], 0)
            self.assertEqual(result["prewarm"]["stderr_bytes"], 0)

    def test_skill_tool_hooks_create_correlated_minimal_events(self):
        payload = {
            "session_id": "session-1",
            "turn_id": "turn-1",
            "tool_name": "Skill",
            "tool_use_id": "call-1",
            "tool_input": {
                "skill": "pdf",
                "access_token": "must-not-leak",
            },
            "cwd": "/tmp/project",
        }
        started = build_codex_hook_envelopes("PreToolUse", payload)
        completed = build_codex_hook_envelopes("PostToolUse", payload)

        self.assertEqual(started[0]["event_type"], "skill.activated")
        self.assertEqual(completed[0]["event_type"], "skill.activation_completed")
        self.assertEqual(completed[0]["parent_event_id"], started[0]["event_id"])
        serialized = json.dumps([started, completed], ensure_ascii=False)
        self.assertNotIn("must-not-leak", serialized)
        self.assertEqual(started[0]["source"]["collection_mode"], "official_hook")

    def test_hook_without_session_identity_is_ignored(self):
        self.assertEqual(
            build_codex_hook_envelopes(
                "PreToolUse", {"tool_name": "Skill", "tool_input": {"skill": "pdf"}}
            ),
            [],
        )

    def test_tool_call_identity_is_scoped_to_agent_session(self):
        first = build_codex_hook_envelopes(
            "PreToolUse",
            {
                "session_id": "session-a",
                "tool_name": "Skill",
                "tool_use_id": "call-1",
                "tool_input": {"skill": "pdf"},
            },
        )
        second = build_codex_hook_envelopes(
            "PreToolUse",
            {
                "session_id": "session-b",
                "tool_name": "Skill",
                "tool_use_id": "call-1",
                "tool_input": {"skill": "pdf"},
            },
        )
        self.assertNotEqual(first[0]["event_id"], second[0]["event_id"])

    def test_claude_explicit_and_slash_skill_activation_are_observed(self):
        explicit = build_claude_hook_envelopes(
            "PreToolUse",
            {
                "session_id": "claude-1",
                "tool_name": "Skill",
                "tool_use_id": "skill-call-1",
                "tool_input": {"skill": "pdf", "token": "must-not-leak"},
            },
        )
        slash = build_claude_hook_envelopes(
            "UserPromptExpansion",
            {
                "session_id": "claude-2",
                "expansion_type": "slash_command",
                "command_name": "pdf",
            },
        )

        self.assertEqual(explicit[0]["event_type"], "skill.activated")
        self.assertEqual(explicit[0]["source"]["adapter"], "claude-code")
        self.assertEqual(explicit[0]["activation_mode"], "explicit_tool")
        self.assertEqual(slash[0]["event_type"], "skill.activated")
        self.assertEqual(slash[0]["activation_mode"], "slash_command")
        self.assertNotIn(
            "must-not-leak", json.dumps(explicit, ensure_ascii=False)
        )

    def test_qoder_skill_hook_uses_the_shared_minimal_event_model(self):
        envelopes = build_qoder_hook_envelopes(
            "PreToolUse",
            {
                "session_id": "qoder-session",
                "tool_name": "Skill",
                "tool_use_id": "qoder-call",
                "tool_input": {
                    "name": "pdf",
                    "secret": "must-not-leak",
                },
                "transcript_path": "/private/qoder/transcript.jsonl",
            },
        )
        self.assertEqual(envelopes[0]["event_type"], "skill.activated")
        self.assertEqual(envelopes[0]["source"]["adapter"], "qoder")
        self.assertEqual(envelopes[0]["skill"]["name"], "pdf")
        serialized = json.dumps(envelopes, ensure_ascii=False)
        self.assertNotIn("must-not-leak", serialized)
        self.assertNotIn("transcript.jsonl", serialized)

    def test_opencode_skill_and_session_error_are_observed(self):
        activated = build_opencode_hook_envelopes(
            "PreToolUse",
            {
                "session_id": "opencode-session",
                "tool_name": "skill",
                "tool_use_id": "opencode-call",
                "tool_input": {"name": "pdf", "content": "must-not-leak"},
            },
        )
        failed = build_opencode_hook_envelopes(
            "SessionError",
            {
                "session_id": "opencode-session",
                "error": "redacted failure",
            },
        )
        self.assertEqual(activated[0]["event_type"], "skill.activated")
        self.assertEqual(activated[0]["source"]["adapter"], "opencode")
        self.assertEqual(failed[0]["event_type"], "turn.failed")
        self.assertEqual(failed[0]["status"], "failed")
        self.assertNotIn(
            "must-not-leak", json.dumps(activated, ensure_ascii=False)
        )

    def test_claude_successful_write_emits_exact_derived_artifact(self):
        envelopes = build_claude_hook_envelopes(
            "PostToolUse",
            {
                "session_id": "claude-write",
                "tool_name": "Write",
                "tool_use_id": "write-call",
                "tool_input": {
                    "file_path": "/tmp/report.md",
                    "content": "private-content",
                },
                "tool_response": {"filePath": "/tmp/report.md"},
            },
        )

        self.assertEqual([item["event_type"] for item in envelopes], [
            "tool.completed",
            "file.created",
        ])
        artifact = envelopes[1]
        self.assertEqual(artifact["payload"]["file_path"], "/tmp/report.md")
        self.assertEqual(artifact["evidence"]["grade"], "derived")
        serialized = json.dumps(envelopes, ensure_ascii=False)
        self.assertNotIn("private-content", serialized)

    def test_claude_file_changed_maps_add_and_unlink_without_content(self):
        created = build_claude_hook_envelopes(
            "FileChanged",
            {
                "session_id": "claude-file",
                "file_path": "/tmp/new.py",
                "event": "add",
                "content": "never-store-this",
            },
        )
        deleted = build_claude_hook_envelopes(
            "FileChanged",
            {
                "session_id": "claude-file",
                "file_path": "/tmp/new.py",
                "event": "unlink",
            },
        )

        self.assertEqual(created[0]["event_type"], "file.created")
        self.assertEqual(created[0]["evidence"]["grade"], "observed")
        self.assertEqual(deleted[0]["event_type"], "file.deleted")
        self.assertNotIn(
            "never-store-this", json.dumps(created, ensure_ascii=False)
        )

    def test_cli_hook_boundary_is_silent_and_fail_open(self):
        root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root / "src")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "skill_runtime_intelligence",
                "hook",
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
            ],
            input=b"{invalid-json",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root),
            env=environment,
            check=False,
            timeout=3,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"")

    def test_lightweight_hook_boundary_is_silent_and_fail_open(self):
        root = Path(__file__).resolve().parents[1]
        environment = dict(os.environ)
        environment["PYTHONPATH"] = str(root / "src")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "skill_runtime_intelligence.hook_cli",
                "--agent",
                "codex",
                "--event",
                "PreToolUse",
            ],
            input=b"{invalid-json",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(root),
            env=environment,
            check=False,
            timeout=3,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"")

    def test_unavailable_collector_queues_and_replays(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / "events.jsonl"
            database = root / "panorama.db"
            envelopes = build_codex_hook_envelopes(
                "PreToolUse",
                {
                    "session_id": "session-queue",
                    "turn_id": "turn-1",
                    "tool_name": "Skill",
                    "tool_use_id": "call-queue",
                    "tool_input": {"skill": "pdf"},
                },
            )
            envelopes[0]["payload"]["api_key"] = "secret-value"

            started_at = time.monotonic()
            delivery = deliver_or_queue(
                envelopes,
                endpoint="http://127.0.0.1:1/api/events",
                queue_path=queue,
                timeout_seconds=0.02,
            )
            elapsed = time.monotonic() - started_at

            self.assertEqual(delivery, "queued")
            self.assertLess(elapsed, 0.5)
            queued = queue.read_text(encoding="utf-8")
            self.assertNotIn("secret-value", queued)
            self.assertIn("[REDACTED]", queued)

            result = drain_event_queue(database, queue)
            self.assertEqual(result["accepted"], 1)
            self.assertEqual(queue.read_text(encoding="utf-8"), "")
            storage = Storage(database)
            try:
                source = storage.list_sources()[0]
                self.assertEqual(source["collection_mode"], "official_hook")
                self.assertEqual(source["role"], "primary")
            finally:
                storage.close()

    def test_running_hook_bridge_ingests_over_private_unix_socket(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            database = root / "panorama.db"
            socket_path = root / "run" / "hook.sock"
            bridge = HookBridge(database, socket_path=socket_path).start()
            try:
                client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                client.connect(str(socket_path))
                header = json.dumps({"event": "PreToolUse"}).encode("utf-8")
                payload = json.dumps(
                    {
                        "session_id": "bridge-session",
                        "turn_id": "turn-1",
                        "tool_name": "Skill",
                        "tool_use_id": "bridge-call",
                        "tool_input": {"skill": "pdf"},
                    }
                ).encode("utf-8")
                client.sendall(header + b"\n" + payload)
                client.close()
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    storage = Storage(database)
                    try:
                        if storage.counts()["normalized_events"] == 1:
                            break
                    finally:
                        storage.close()
                    time.sleep(0.02)
                storage = Storage(database)
                try:
                    self.assertEqual(storage.counts()["normalized_events"], 1)
                    self.assertEqual(
                        storage.list_sources()[0]["collection_mode"],
                        "official_hook",
                    )
                finally:
                    storage.close()
                self.assertEqual(socket_path.stat().st_mode & 0o777, 0o600)
            finally:
                bridge.close()
            self.assertFalse(socket_path.exists())

    def test_optional_native_sender_delivers_to_hook_bridge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            built = build_native_hook_sender(root)
            if not built["available"]:
                self.skipTest(built["reason"])
            database = root / "panorama.db"
            socket_path = root / "run" / "hook.sock"
            bridge = HookBridge(database, socket_path=socket_path).start()
            try:
                result = subprocess.run(
                    [
                        built["path"],
                        "--agent",
                        "codex",
                        "--event",
                        "PreToolUse",
                        "--socket",
                        str(socket_path),
                    ],
                    input=json.dumps(
                        {
                            "session_id": "native-session",
                            "turn_id": "turn-1",
                            "tool_name": "Skill",
                            "tool_use_id": "native-call",
                            "tool_input": {"skill": "pdf"},
                        }
                    ).encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=2,
                )
                self.assertEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b"")
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    storage = Storage(database)
                    try:
                        if storage.counts()["normalized_events"] == 1:
                            break
                    finally:
                        storage.close()
                    time.sleep(0.02)
                storage = Storage(database)
                try:
                    self.assertEqual(storage.counts()["normalized_events"], 1)
                finally:
                    storage.close()
            finally:
                bridge.close()

    def test_native_sender_ingests_qoder_and_opencode_as_distinct_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            built = build_native_hook_sender(root)
            if not built["available"]:
                self.skipTest(built["reason"])
            database = root / "panorama.db"
            socket_path = root / "run" / "hook.sock"
            bridge = HookBridge(database, socket_path=socket_path).start()
            try:
                for agent in ("qoder", "opencode"):
                    result = subprocess.run(
                        [
                            built["path"],
                            "--agent",
                            agent,
                            "--event",
                            "PreToolUse",
                            "--socket",
                            str(socket_path),
                        ],
                        input=json.dumps(
                            {
                                "session_id": f"{agent}-session",
                                "tool_name": "Skill",
                                "tool_use_id": f"{agent}-call",
                                "tool_input": {"name": "pdf"},
                            }
                        ).encode("utf-8"),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                        timeout=2,
                    )
                    self.assertEqual(result.returncode, 0)
                deadline = time.monotonic() + 2
                while time.monotonic() < deadline:
                    storage = Storage(database)
                    try:
                        if storage.counts()["normalized_events"] == 2:
                            break
                    finally:
                        storage.close()
                    time.sleep(0.02)
                storage = Storage(database)
                try:
                    sources = storage.list_sources()
                    self.assertEqual(
                        {source["adapter"] for source in sources},
                        {"qoder", "opencode"},
                    )
                    self.assertTrue(
                        all(
                            source["collection_mode"] == "official_hook"
                            for source in sources
                        )
                    )
                finally:
                    storage.close()
            finally:
                bridge.close()


class HookIntegrationTests(unittest.TestCase):
    def test_enable_is_additive_idempotent_and_exactly_removable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "hooks.json"
            state_root = root / "state"
            existing = {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "*",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "rapid-tele agent hook --event PostToolUse",
                                    "timeout": 15,
                                }
                            ],
                        }
                    ]
                }
            }
            config.write_text(json.dumps(existing), encoding="utf-8")
            config.chmod(0o640)

            before = inspect_codex_integration(config, "/tmp/skill-runtime")
            self.assertFalse(before["installed"])
            first = enable_codex_hooks(
                "/tmp/skill-runtime", config, state_root=state_root
            )
            second = enable_codex_hooks(
                "/tmp/skill-runtime", config, state_root=state_root
            )
            enabled = json.loads(config.read_text(encoding="utf-8"))

            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(
                set(first["added_events"]), set(MANAGED_CODEX_EVENTS)
            )
            self.assertNotIn("PostToolUseFailure", MANAGED_CODEX_EVENTS)
            self.assertIn("PreCompact", MANAGED_CODEX_EVENTS)
            self.assertIn("PostCompact", MANAGED_CODEX_EVENTS)
            self.assertEqual(
                enabled["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
                "rapid-tele agent hook --event PostToolUse",
            )
            self.assertEqual(config.stat().st_mode & 0o777, 0o640)
            self.assertTrue(
                (state_root / "integrations" / "codex.json").exists()
            )
            self.assertEqual(
                len(list(root.glob("hooks.json.skill-runtime.bak.*"))), 1
            )

            removed = remove_codex_hooks(config, state_root=state_root)
            final = json.loads(config.read_text(encoding="utf-8"))
            self.assertTrue(removed["changed"])
            self.assertEqual(
                set(removed["removed_events"]), set(MANAGED_CODEX_EVENTS)
            )
            self.assertEqual(final, existing)
            self.assertFalse(
                (state_root / "integrations" / "codex.json").exists()
            )

    def test_codex_stop_hooks_return_empty_json_without_blocking(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "hooks.json"
            enable_codex_hooks(
                "/tmp/skill-runtime", config, state_root=root / "state"
            )
            enabled = json.loads(config.read_text(encoding="utf-8"))
            for event in ("Stop", "SubagentStop"):
                command = enabled["hooks"][event][0]["hooks"][0]["command"]
                self.assertIn("printf '%s\\n' '{}'", command)
                self.assertIn("|| true", command)

    def test_prefers_installed_lightweight_hook_entrypoint(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = root / "skill-runtime"
            fast_hook = root / "skill-runtime-hook"
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            fast_hook.write_text("#!/bin/sh\n", encoding="utf-8")
            config = root / "hooks.json"

            result = enable_codex_hooks(
                str(executable), config, state_root=root / "state"
            )
            enabled = json.loads(config.read_text(encoding="utf-8"))
            commands = [
                hook["command"]
                for groups in enabled["hooks"].values()
                for group in groups
                for hook in group["hooks"]
            ]

            self.assertTrue(result["changed"])
            self.assertTrue(all(str(fast_hook) in command for command in commands))
            if platform.system() != "Darwin":
                self.assertTrue(
                    all("/usr/bin/nc -N -U" in command for command in commands)
                )
            removed = remove_codex_hooks(config, state_root=root / "state")
            self.assertTrue(removed["changed"])
            self.assertEqual(
                json.loads(config.read_text(encoding="utf-8")), {"hooks": {}}
            )

    def test_claude_hooks_are_async_additive_and_exactly_removable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            state_root = root / "state"
            existing = {
                "permissions": {"allow": ["Read"]},
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Write",
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "other-observer",
                                }
                            ],
                        }
                    ]
                },
            }
            settings.write_text(json.dumps(existing), encoding="utf-8")

            self.assertFalse(
                inspect_claude_integration(
                    settings, "/tmp/skill-runtime"
                )["installed"]
            )
            first = enable_claude_hooks(
                "/tmp/skill-runtime", settings, state_root=state_root
            )
            second = enable_claude_hooks(
                "/tmp/skill-runtime", settings, state_root=state_root
            )
            enabled = json.loads(settings.read_text(encoding="utf-8"))
            managed = [
                hook
                for groups in enabled["hooks"].values()
                for group in groups
                for hook in group.get("hooks", [])
                if "--managed-by skill-runtime-intelligence"
                in hook.get("command", "")
            ]

            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            self.assertEqual(set(first["added_events"]), set(MANAGED_CLAUDE_EVENTS))
            self.assertTrue(all(hook.get("async") is True for hook in managed))
            self.assertTrue(
                all("--agent claude-code" in hook["command"] for hook in managed)
            )
            self.assertNotIn("FileChanged", first["installed_events"])
            self.assertEqual(
                enabled["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
                "other-observer",
            )

            removed = remove_claude_hooks(settings, state_root=state_root)
            self.assertTrue(removed["changed"])
            self.assertEqual(
                json.loads(settings.read_text(encoding="utf-8")), existing
            )

    def test_qoder_hooks_are_additive_fail_open_and_exactly_removable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / "settings.json"
            settings.write_text(
                json.dumps(
                    {
                        "general": {"enableAutoUpdate": False},
                        "hooks": {
                            "PostToolUse": [
                                {
                                    "matcher": "Bash",
                                    "hooks": [
                                        {
                                            "type": "command",
                                            "command": "/tmp/unrelated",
                                        }
                                    ],
                                }
                            ]
                        },
                    }
                ),
                encoding="utf-8",
            )
            state_root = root / "state"
            result = enable_qoder_hooks(
                "/tmp/skill-runtime",
                settings,
                state_root=state_root,
            )
            self.assertTrue(result["changed"])
            inspected = inspect_qoder_integration(
                settings,
                "/tmp/skill-runtime",
                state_root=state_root,
            )
            self.assertTrue(inspected["installed"])
            configured = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(configured["general"]["enableAutoUpdate"], False)
            managed = [
                hook
                for groups in configured["hooks"].values()
                for group in groups
                for hook in group.get("hooks", [])
                if "--agent qoder" in hook.get("command", "")
            ]
            self.assertEqual(len(managed), len(MANAGED_QODER_EVENTS))
            self.assertTrue(all("|| true" in hook["command"] for hook in managed))
            removed = remove_qoder_hooks(settings, state_root=state_root)
            self.assertTrue(removed["changed"])
            remaining = json.loads(settings.read_text(encoding="utf-8"))
            self.assertEqual(
                remaining["hooks"]["PostToolUse"][0]["hooks"][0]["command"],
                "/tmp/unrelated",
            )

    def test_opencode_plugin_is_owned_idempotent_and_exactly_removable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plugin = root / "opencode" / "plugins" / "skill-runtime.js"
            state_root = root / "state"
            first = enable_opencode_plugin(
                "/tmp/skill-runtime",
                plugin,
                state_root=state_root,
            )
            second = enable_opencode_plugin(
                "/tmp/skill-runtime",
                plugin,
                state_root=state_root,
            )
            self.assertTrue(first["changed"])
            self.assertFalse(second["changed"])
            source = plugin.read_text(encoding="utf-8")
            self.assertIn("managed-by: skill-runtime-intelligence", source)
            self.assertIn('"chat.message": async', source)
            self.assertIn('"tool.execute.before": "PreToolUse"', source)
            self.assertIn('"tool.execute.after": async', source)
            self.assertIn("fallbackOnce", source)
            self.assertIn("spawnFallback", source)
            self.assertNotIn('session.hook("request"', source)
            inspected = inspect_opencode_integration(
                plugin,
                "/tmp/skill-runtime",
                state_root=state_root,
            )
            self.assertTrue(inspected["installed"])
            removed = remove_opencode_plugin(plugin, state_root=state_root)
            self.assertTrue(removed["changed"])
            self.assertFalse(plugin.exists())


if __name__ == "__main__":
    unittest.main()
