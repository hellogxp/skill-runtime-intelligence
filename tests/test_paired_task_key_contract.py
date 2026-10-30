import json
import tempfile
import unittest
from pathlib import Path

from experiments.cross_agent.paired_task_key_contract_benchmark import (
    _assignment,
    run_benchmark,
)
from experiments.privacy_safe_paired_task_key import paired_task_key


class PairedTaskKeyContractTests(unittest.TestCase):
    def test_key_is_stable_and_domain_separated(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / "study.secret"
            base = _assignment(
                "task-a",
                scope="study-a",
                protocol="v1",
            )
            repeated = paired_task_key(secret, base)
            self.assertEqual(repeated, paired_task_key(secret, dict(base)))
            self.assertNotEqual(
                repeated["task_key"],
                paired_task_key(
                    secret,
                    _assignment(
                        "task-b",
                        scope="study-a",
                        protocol="v1",
                    ),
                )["task_key"],
            )
            self.assertNotEqual(
                repeated["task_key"],
                paired_task_key(
                    secret,
                    _assignment(
                        "task-a",
                        scope="study-b",
                        protocol="v1",
                    ),
                )["task_key"],
            )

    def test_key_requires_explicit_task_assignment(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = Path(directory) / "study.secret"
            with self.assertRaises(ValueError):
                paired_task_key(
                    secret,
                    {
                        "schema_version": "sri.paired-task-assignment.v1",
                        "study_scope": "study-a",
                        "protocol_version": "v1",
                        "prompt": "do not infer a task key from content",
                    },
                )
            self.assertFalse(secret.exists())

    def test_benchmark_passes_without_exporting_raw_identifiers(self):
        report = run_benchmark(trials=2, task_pool_size=16)
        serialized = json.dumps(report, sort_keys=True)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["passed_trials"], 2)
        self.assertEqual(report["metrics"]["agent_derivations"], 6)
        self.assertEqual(report["metrics"]["task_keys_generated"], 40)
        self.assertNotIn("opaque-task-", serialized)
        self.assertNotIn("pool-task-", serialized)


if __name__ == "__main__":
    unittest.main()
