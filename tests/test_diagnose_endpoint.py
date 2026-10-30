"""Tests for the stateless diagnosis endpoint.

The endpoint exists so a remote host can reuse the one diagnosis
implementation instead of reimplementing evidence semantics. These tests pin the
contract that such a host depends on: a versioned payload, strict input
validation, capability-aware defaults, and explicit degradation when the Skill
definition is not available.
"""

import json
import threading
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from skill_runtime_intelligence.diagnosis_engine import DIAGNOSIS_SCHEMA_VERSION
from skill_runtime_intelligence.server import create_server


def _events():
    return [
        {
            "event_id": "evt_1",
            "event_type": "turn.started",
            "stage": "request",
            "evidence_grade": "observed",
            "status": "completed",
        },
        {
            "event_id": "evt_2",
            "event_type": "skill.activated",
            "stage": "activation",
            "evidence_grade": "observed",
            "status": "completed",
        },
        {
            "event_id": "evt_3",
            "event_type": "tool.failed",
            "stage": "execution",
            "evidence_grade": "observed",
            "status": "failed",
        },
    ]


def _run():
    return {
        "name": "pdf",
        "adapter": "otel",
        "activation_mode": "explicit_tool",
        "source_path": "collector://pdf/SKILL.md",
    }


class DiagnoseEndpointTest(unittest.TestCase):
    def _post(self, base_url, body):
        request = Request(
            f"{base_url}/api/diagnose",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:
            return json.loads(response.read())

    def _serve(self):
        directory = TemporaryDirectory()
        root = Path(directory.name)
        server = create_server(root / "panorama.db", "127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base_url = f"http://127.0.0.1:{server.server_address[1]}"

        def cleanup():
            server.shutdown()
            server.server_close()
            directory.cleanup()

        return base_url, cleanup

    def test_returns_versioned_payload(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(
                base_url, {"run": _run(), "events": _events()}
            )
        finally:
            cleanup()

        self.assertEqual(payload["schema_version"], DIAGNOSIS_SCHEMA_VERSION)
        for key in (
            "stage_summary",
            "evidence_completeness",
            "first_gap",
            "narrative",
            "adapter_capabilities",
            "activity_summary",
            "behavior_assessment",
            "findings",
            "assessment",
        ):
            self.assertIn(key, payload)

    def test_stage_summary_covers_all_eight_stages(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(base_url, {"run": _run(), "events": _events()})
        finally:
            cleanup()

        self.assertEqual(len(payload["stage_summary"]), 8)
        stages = [item["stage"] for item in payload["stage_summary"]]
        self.assertEqual(stages[0], "request")
        self.assertEqual(stages[-1], "outcome")

    def test_absent_stage_is_not_observed_not_failed(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(base_url, {"run": _run(), "events": _events()})
        finally:
            cleanup()

        by_stage = {item["stage"]: item for item in payload["stage_summary"]}
        # No resource evidence was sent, so the stage must report missing
        # evidence rather than a failure.
        self.assertIn(
            by_stage["resources"]["status"], {"not_observed", "unsupported"}
        )
        self.assertNotEqual(by_stage["resources"]["status"], "failed")

    def test_unknown_adapter_defaults_to_declared_matrix(self):
        base_url, cleanup = self._serve()
        run = _run()
        run["adapter"] = "an-adapter-that-does-not-exist"
        try:
            payload = self._post(base_url, {"run": run, "events": _events()})
        finally:
            cleanup()

        # An unknown adapter must still receive a capability matrix instead of
        # being assumed fully observable.
        self.assertEqual(len(payload["adapter_capabilities"]), 8)

    def test_behavior_assessment_degrades_without_definition(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(base_url, {"run": _run(), "events": _events()})
        finally:
            cleanup()

        behavior = payload["behavior_assessment"]
        self.assertEqual(behavior["source_status"], "unavailable")
        self.assertTrue(behavior["limitation"])

    def test_injected_definition_enables_constraint_evaluation(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(
                base_url,
                {
                    "run": _run(),
                    "events": _events(),
                    "skill_source_content": (
                        "# pdf\n\nAlways run `pytest` before reporting success.\n"
                    ),
                },
            )
        finally:
            cleanup()

        self.assertNotEqual(
            payload["behavior_assessment"]["source_status"], "unavailable"
        )

    def test_explicit_capabilities_are_honoured(self):
        base_url, cleanup = self._serve()
        capabilities = {
            "request": "supported",
            "discovery": "unsupported",
            "activation": "supported",
            "instructions": "supported",
            "resources": "supported",
            "execution": "supported",
            "artifacts": "unsupported",
            "outcome": "supported",
        }
        try:
            payload = self._post(
                base_url,
                {
                    "run": _run(),
                    "events": _events(),
                    "capabilities": capabilities,
                },
            )
        finally:
            cleanup()

        by_stage = {item["stage"]: item for item in payload["stage_summary"]}
        self.assertEqual(by_stage["discovery"]["status"], "unsupported")
        self.assertEqual(by_stage["artifacts"]["status"], "unsupported")

    def test_missing_run_is_rejected(self):
        base_url, cleanup = self._serve()
        try:
            with self.assertRaises(HTTPError) as error:
                self._post(base_url, {"events": _events()})
        finally:
            cleanup()

        self.assertEqual(error.exception.code, 400)

    def test_run_without_name_is_rejected(self):
        base_url, cleanup = self._serve()
        try:
            with self.assertRaises(HTTPError) as error:
                self._post(base_url, {"run": {"adapter": "otel"}})
        finally:
            cleanup()

        self.assertEqual(error.exception.code, 400)

    def test_non_array_events_is_rejected(self):
        base_url, cleanup = self._serve()
        try:
            with self.assertRaises(HTTPError) as error:
                self._post(base_url, {"run": _run(), "events": "not-a-list"})
        finally:
            cleanup()

        self.assertEqual(error.exception.code, 400)

    def test_non_string_source_content_is_rejected(self):
        base_url, cleanup = self._serve()
        try:
            with self.assertRaises(HTTPError) as error:
                self._post(
                    base_url,
                    {
                        "run": _run(),
                        "events": _events(),
                        "skill_source_content": {"not": "a string"},
                    },
                )
        finally:
            cleanup()

        self.assertEqual(error.exception.code, 400)

    def test_empty_event_list_still_produces_a_payload(self):
        base_url, cleanup = self._serve()
        try:
            payload = self._post(base_url, {"run": _run(), "events": []})
        finally:
            cleanup()

        # A run with no events is a valid observation: nothing was seen.
        self.assertEqual(payload["schema_version"], DIAGNOSIS_SCHEMA_VERSION)
        self.assertEqual(len(payload["stage_summary"]), 8)

    def test_endpoint_does_not_persist_anything(self):
        """The endpoint is a projection, not an ingest path."""

        base_url, cleanup = self._serve()
        try:
            self._post(base_url, {"run": _run(), "events": _events()})
            with urlopen(f"{base_url}/api/runs", timeout=5) as response:
                runs = json.loads(response.read())
        finally:
            cleanup()

        # Diagnosing must not create a run; ingest stays the only writer.
        self.assertEqual(runs.get("runs", []), [])


if __name__ == "__main__":
    unittest.main()
