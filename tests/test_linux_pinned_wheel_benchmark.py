import tempfile
import unittest
import zipfile
from pathlib import Path

from experiments.product_lifecycle.linux_pinned_wheel_benchmark import (
    _analyze_wheels,
)


class LinuxPinnedWheelBenchmarkTests(unittest.TestCase):
    def test_timestamp_only_rebuild_pair_passes(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-linux-wheel-analysis-test-"
        ) as directory:
            root = Path(directory)
            published = root / "published.whl"
            rebuilt_a = root / "rebuilt-a.whl"
            rebuilt_b = root / "rebuilt-b.whl"
            for path, timestamp in (
                (published, (2026, 7, 30, 12, 0, 0)),
                (rebuilt_a, (1980, 1, 1, 0, 0, 0)),
                (rebuilt_b, (1980, 1, 1, 0, 0, 0)),
            ):
                with zipfile.ZipFile(path, "w") as archive:
                    info = zipfile.ZipInfo(
                        "package-1.0.dist-info/METADATA",
                        timestamp,
                    )
                    archive.writestr(
                        info,
                        b"Metadata-Version: 2.4\nName: package\nVersion: 1.0\n",
                    )
                    wheel = zipfile.ZipInfo(
                        "package-1.0.dist-info/WHEEL",
                        timestamp,
                    )
                    archive.writestr(
                        wheel,
                        b"Wheel-Version: 1.0\nTag: py3-none-any\n",
                    )

            result = _analyze_wheels(
                published,
                [rebuilt_a, rebuilt_b],
            )

        self.assertTrue(result["passed"])
        self.assertTrue(result["normalized_content_match"])
        self.assertTrue(result["repeated_digest_match"])
        self.assertFalse(result["raw_digest_match"])


if __name__ == "__main__":
    unittest.main()
