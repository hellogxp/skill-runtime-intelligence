import hashlib
import unittest
from pathlib import Path

from experiments.product_lifecycle.migration_release_artifact_contract_benchmark import (
    run_benchmark,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCAL_V010_WHEEL = (
    REPOSITORY_ROOT
    / "dist"
    / "skill_runtime_intelligence-0.1.0-py3-none-any.whl"
)


class MigrationReleaseArtifactContractBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        LOCAL_V010_WHEEL.is_file(),
        "run scripts/fetch_release_fixtures.py --version 0.1.0 first",
    )
    def test_identity_verified_wheel_contract_migrates(self):
        digest = hashlib.sha256(LOCAL_V010_WHEEL.read_bytes()).hexdigest()
        report = run_benchmark(
            artifact=LOCAL_V010_WHEEL,
            expected_sha256=digest,
            expected_version="0.1.0",
            trials=1,
        )

        self.assertTrue(report["gate"]["passed"])
        self.assertTrue(report["artifact"]["identity_verified"])
        self.assertTrue(report["artifact"]["installed_version_matches"])
        self.assertEqual(report["metrics"]["evaluations"], 1)
        self.assertEqual(report["metrics"]["passed"], 1)


if __name__ == "__main__":
    unittest.main()
