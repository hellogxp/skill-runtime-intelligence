import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from experiments.product_lifecycle.sdist_rebuild_determinism_benchmark import (
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


class SdistRebuildDeterminismBenchmarkTests(unittest.TestCase):
    @unittest.skipUnless(
        WHEEL.is_file() and SDIST.is_file(),
        "verified v0.1.0 release artifacts are not installed; "
        "run scripts/fetch_release_fixtures.py --version 0.1.0",
    )
    def test_fixed_epoch_rebuild_repeats(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-fixed-epoch-test-"
        ) as directory:
            root = Path(directory)
            wheel_manifest = root / "wheel.json"
            sdist_manifest = root / "sdist.json"
            wheel_manifest.write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {
                                "version": "0.1.0",
                                "filename": WHEEL.name,
                                "sha256": hashlib.sha256(
                                    WHEEL.read_bytes()
                                ).hexdigest(),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            sdist_manifest.write_text(
                json.dumps(
                    {
                        "artifacts": [
                            {
                                "version": "0.1.0",
                                "filename": SDIST.name,
                                "sha256": hashlib.sha256(
                                    SDIST.read_bytes()
                                ).hexdigest(),
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            report = run_benchmark(
                wheel_manifest,
                sdist_manifest,
                REPOSITORY_ROOT / "dist",
                build_repetitions=2,
            )

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(
            report["metrics"]["fixed_epoch_repeatable_pairs"],
            1,
        )
        self.assertEqual(report["metrics"]["contract_parity_pairs"], 1)


if __name__ == "__main__":
    unittest.main()
