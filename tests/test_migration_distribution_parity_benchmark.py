import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experiments.product_lifecycle.migration_distribution_parity_benchmark import (
    run_benchmark,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
WHEEL = (
    REPOSITORY_ROOT
    / "dist"
    / "skill_runtime_intelligence-0.1.0-py3-none-any.whl"
)
SDIST = (
    REPOSITORY_ROOT
    / "dist"
    / "skill_runtime_intelligence-0.1.0.tar.gz"
)


class MigrationDistributionParityBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        WHEEL.is_file() and SDIST.is_file(),
        "run scripts/fetch_release_fixtures.py --version 0.1.0 first",
    )
    def test_local_v010_distribution_pair(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-distribution-parity-test-"
        ) as directory:
            root = Path(directory)
            wheel_manifest = root / "wheel.json"
            sdist_manifest = root / "sdist.json"
            base = {
                "repository": "fixture/repository",
                "queried_at": "2026-07-30T00:00:00Z",
                "evidence_grade": "Experimental",
            }
            wheel_manifest.write_text(
                json.dumps(
                    {
                        **base,
                        "artifacts": [
                            {
                                "version": "0.1.0",
                                "filename": WHEEL.name,
                                "sha256": hashlib.sha256(
                                    WHEEL.read_bytes()
                                ).hexdigest(),
                                "url": "fixture:wheel",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            sdist_manifest.write_text(
                json.dumps(
                    {
                        **base,
                        "artifacts": [
                            {
                                "version": "0.1.0",
                                "filename": SDIST.name,
                                "sha256": hashlib.sha256(
                                    SDIST.read_bytes()
                                ).hexdigest(),
                                "url": "fixture:sdist",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            report = run_benchmark(
                wheel_manifest,
                sdist_manifest,
                REPOSITORY_ROOT / "dist",
                trials=1,
            )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["completed_pairs"], 1)
        self.assertEqual(report["metrics"]["schema_parity_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
