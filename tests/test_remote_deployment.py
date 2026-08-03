import base64
import json
import shutil
import ssl
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from skill_runtime_intelligence.event_queue import (
    append_event_queue,
    drain_remote_event_queue,
)
from skill_runtime_intelligence.remote_access import (
    build_remote_access,
    initialize_remote_secrets,
    read_secret_file,
)
from skill_runtime_intelligence.server import create_server
from tests.test_collector import fixture_event


def _write_token(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n", encoding="utf-8")
    path.chmod(0o600)


def _viewer_header(token: str) -> str:
    encoded = base64.b64encode(f"sri:{token}".encode("utf-8")).decode("ascii")
    return f"Basic {encoded}"


class RemoteAccessTests(unittest.TestCase):
    def test_remote_init_creates_separate_private_secrets_without_values(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            result = initialize_remote_secrets(root)
            viewer = Path(result["viewer_token_file"])
            ingest = Path(result["ingest_token_file"])
            self.assertEqual(set(result["created"]), {"viewer", "ingest"})
            self.assertFalse(result["tokens_printed"])
            self.assertNotEqual(read_secret_file(viewer), read_secret_file(ingest))
            self.assertEqual(viewer.stat().st_mode & 0o777, 0o600)
            self.assertEqual(ingest.stat().st_mode & 0o777, 0o600)

            repeated = initialize_remote_secrets(root)
            self.assertEqual(repeated["created"], [])
            self.assertEqual(set(repeated["existing"]), {"viewer", "ingest"})

    def test_remote_mode_fails_closed_without_auth_and_https_boundary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            viewer = root / "viewer.token"
            ingest = root / "ingest.token"
            _write_token(viewer, "v" * 40)
            _write_token(ingest, "i" * 40)

            with self.assertRaisesRegex(ValueError, "non-loopback"):
                build_remote_access(enabled=False, host="0.0.0.0")
            with self.assertRaisesRegex(ValueError, "direct TLS"):
                build_remote_access(
                    enabled=True,
                    host="127.0.0.1",
                    viewer_token_file=viewer,
                    ingest_token_file=ingest,
                )
            with self.assertRaisesRegex(ValueError, "loopback"):
                build_remote_access(
                    enabled=True,
                    host="0.0.0.0",
                    viewer_token_file=viewer,
                    ingest_token_file=ingest,
                    behind_https_proxy=True,
                )

            _write_token(ingest, "v" * 40)
            with self.assertRaisesRegex(ValueError, "must be different"):
                build_remote_access(
                    enabled=True,
                    host="127.0.0.1",
                    viewer_token_file=viewer,
                    ingest_token_file=ingest,
                    behind_https_proxy=True,
                )
            _write_token(ingest, "i" * 40)

            access = build_remote_access(
                enabled=True,
                host="127.0.0.1",
                viewer_token_file=viewer,
                ingest_token_file=ingest,
                behind_https_proxy=True,
            )
            self.assertTrue(access.enabled)
            self.assertEqual(access.transport, "https_proxy")

    def test_remote_server_enforces_independent_viewer_and_ingest_roles(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            viewer_token = "viewer-" + "v" * 36
            ingest_token = "ingest-" + "i" * 36
            viewer = root / "viewer.token"
            ingest = root / "ingest.token"
            _write_token(viewer, viewer_token)
            _write_token(ingest, ingest_token)
            access = build_remote_access(
                enabled=True,
                host="127.0.0.1",
                viewer_token_file=viewer,
                ingest_token_file=ingest,
                behind_https_proxy=True,
            )
            server = create_server(
                root / "panorama.db",
                "127.0.0.1",
                0,
                remote_access=access,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base_url = f"http://127.0.0.1:{server.server_address[1]}"
            try:
                with urlopen(f"{base_url}/api/health", timeout=3) as response:
                    public_health = json.loads(response.read())
                self.assertTrue(public_health["auth_required"])
                self.assertNotIn("counts", public_health)

                with self.assertRaises(HTTPError) as missing_viewer:
                    urlopen(f"{base_url}/api/runs", timeout=3)
                self.assertEqual(missing_viewer.exception.code, 401)

                request = Request(
                    f"{base_url}/api/runs",
                    headers={"Authorization": _viewer_header(viewer_token)},
                )
                with urlopen(request, timeout=3) as response:
                    self.assertEqual(json.loads(response.read()), {"runs": []})

                viewer_settings = Request(
                    f"{base_url}/api/settings",
                    data=b'{"retention_days":30}',
                    headers={
                        "Authorization": _viewer_header(viewer_token),
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as read_only:
                    urlopen(viewer_settings, timeout=3)
                self.assertEqual(read_only.exception.code, 403)

                body = json.dumps(fixture_event("evt-remote")).encode("utf-8")
                viewer_ingest = Request(
                    f"{base_url}/api/events",
                    data=body,
                    headers={
                        "Authorization": _viewer_header(viewer_token),
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with self.assertRaises(HTTPError) as wrong_role:
                    urlopen(viewer_ingest, timeout=3)
                self.assertEqual(wrong_role.exception.code, 401)

                collector_ingest = Request(
                    f"{base_url}/api/events",
                    data=body,
                    headers={
                        "Authorization": f"Bearer {ingest_token}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urlopen(collector_ingest, timeout=3) as response:
                    accepted = json.loads(response.read())
                self.assertEqual(accepted["accepted"], 1)

                request = Request(
                    f"{base_url}/api/health",
                    headers={"Authorization": _viewer_header(viewer_token)},
                )
                with urlopen(request, timeout=3) as response:
                    private_health = json.loads(response.read())
                self.assertEqual(private_health["counts"]["normalized_events"], 1)
                self.assertEqual(private_health["deployment"], "self_hosted_remote")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    def test_remote_relay_preserves_queue_on_auth_failure_then_drains(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            viewer_token = "viewer-" + "v" * 36
            ingest_token = "ingest-" + "i" * 36
            viewer = root / "viewer.token"
            ingest = root / "ingest.token"
            _write_token(viewer, viewer_token)
            _write_token(ingest, ingest_token)
            access = build_remote_access(
                enabled=True,
                host="127.0.0.1",
                viewer_token_file=viewer,
                ingest_token_file=ingest,
                behind_https_proxy=True,
            )
            server = create_server(
                root / "panorama.db",
                "127.0.0.1",
                0,
                remote_access=access,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            endpoint = f"http://127.0.0.1:{server.server_address[1]}/api/events"
            queue = root / "queue" / "events.jsonl"
            append_event_queue(queue, [fixture_event("evt-relay")])
            try:
                failed = drain_remote_event_queue(endpoint, "x" * 40, queue)
                self.assertFalse(failed["connected"])
                self.assertEqual(failed["remaining"], 1)
                self.assertTrue(queue.read_text(encoding="utf-8").strip())

                delivered = drain_remote_event_queue(endpoint, ingest_token, queue)
                self.assertTrue(delivered["connected"])
                self.assertEqual(delivered["delivered"], 1)
                self.assertEqual(delivered["remaining"], 0)
                self.assertEqual(queue.read_text(encoding="utf-8"), "")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)

    @unittest.skipUnless(shutil.which("openssl"), "openssl is required")
    def test_direct_tls_remote_service_serves_https(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            viewer = root / "viewer.token"
            ingest = root / "ingest.token"
            cert = root / "cert.pem"
            key = root / "key.pem"
            _write_token(viewer, "v" * 40)
            _write_token(ingest, "i" * 40)
            subprocess.run(
                [
                    shutil.which("openssl"),
                    "req",
                    "-x509",
                    "-newkey",
                    "rsa:2048",
                    "-nodes",
                    "-keyout",
                    str(key),
                    "-out",
                    str(cert),
                    "-subj",
                    "/CN=localhost",
                    "-days",
                    "1",
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
            )
            key.chmod(0o600)
            access = build_remote_access(
                enabled=True,
                host="127.0.0.1",
                viewer_token_file=viewer,
                ingest_token_file=ingest,
                tls_cert=cert,
                tls_key=key,
            )
            server = create_server(
                root / "panorama.db",
                "127.0.0.1",
                0,
                remote_access=access,
            )
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            try:
                with urlopen(
                    f"https://127.0.0.1:{server.server_address[1]}/api/health",
                    timeout=3,
                    context=context,
                ) as response:
                    health = json.loads(response.read())
                self.assertEqual(health["transport"], "direct_tls")
                self.assertTrue(health["auth_required"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)


if __name__ == "__main__":
    unittest.main()
