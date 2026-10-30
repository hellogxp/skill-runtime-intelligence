import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experiments.product_lifecycle.migration_release_matrix_benchmark import (
    run_benchmark,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LOCAL_WHEEL = (
    REPOSITORY_ROOT
    / "dist"
    / "skill_runtime_intelligence-0.1.0-py3-none-any.whl"
)


class MigrationReleaseMatrixBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        LOCAL_WHEEL.is_file(),
        "run scripts/fetch_release_fixtures.py --version 0.1.0 first",
    )
    def test_single_verified_artifact_matrix(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-release-matrix-test-"
        ) as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": "test",
                        "repository": "test/repository",
                        "queried_at": "2026-07-30T00:00:00Z",
                        "evidence_grade": "Experimental",
                        "artifacts": [
                            {
                                "version": "0.1.0",
                                "tag": "v0.1.0",
                                "filename": LOCAL_WHEEL.name,
                                "sha256": hashlib.sha256(
                                    LOCAL_WHEEL.read_bytes()
                                ).hexdigest(),
                                "url": "fixture:local-wheel",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_benchmark(manifest, LOCAL_WHEEL.parent, trials=1)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["completed_artifacts"], 1)
        self.assertEqual(report["metrics"]["migration_evaluations"], 1)


if __name__ == "__main__":
    unittest.main()
