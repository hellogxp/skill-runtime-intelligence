import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from experiments.external_validity.run_multirepo_agent_benchmark import (
    FAULT_MODES,
    _parse_repository_overrides,
    _skill_body,
)


class MultirepoExternalValidityTests(unittest.TestCase):
    def test_frozen_profile_matrix_has_six_repositories_and_skills(self):
        manifest = json.loads(Path("experiments/external_validity/multirepo_profiles.json").read_text())
        profiles = manifest["profiles"]
        self.assertEqual(len(profiles), 6)
        self.assertEqual(len({item["repo_key"] for item in profiles}), 6)
        self.assertEqual(len({item["skill_id"] for item in profiles}), 6)
        self.assertTrue(all(len(item["files"]) == 3 for item in profiles))

    def test_fault_matrix_contains_clean_and_six_faults(self):
        self.assertEqual(len(FAULT_MODES), 7)
        self.assertIn("clean", FAULT_MODES)
        self.assertIn("verifier_conflict", FAULT_MODES)

    def test_skill_requires_probe_and_read_only_operation(self):
        body = _skill_body({"skill_id": "demo", "description": "demo"})
        self.assertIn("scripts/probe.py", body)
        self.assertIn("Do not modify", body)

    def test_repository_override(self):
        with tempfile.TemporaryDirectory() as directory:
            result = _parse_repository_overrides([f"tinylru={directory}"])
            self.assertEqual(result["tinylru"], Path(directory).resolve())

    def test_repository_defaults_use_configurable_root(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict("os.environ", {"SRI_BENCHMARK_ROOT": directory}):
                result = _parse_repository_overrides([])
            root = Path(directory).resolve()
            self.assertEqual(result["tinylru"], root / "tinylru")
            self.assertEqual(result["rapid-agent"], root / "rapid" / "RAPID-Agent")


if __name__ == "__main__":
    unittest.main()
