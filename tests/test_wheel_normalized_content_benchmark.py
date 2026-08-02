import tempfile
import unittest
import zipfile
from pathlib import Path

from experiments.product_lifecycle.wheel_normalized_content_benchmark import (
    _normalized_wheel_manifest,
)


class WheelNormalizedContentBenchmarkTests(unittest.TestCase):
    def test_timestamp_only_difference_normalizes(self):
        with tempfile.TemporaryDirectory(
            prefix="sri-wheel-normalization-test-"
        ) as directory:
            root = Path(directory)
            first = root / "first.whl"
            second = root / "second.whl"
            for path, timestamp in (
                (first, (2026, 7, 30, 10, 0, 0)),
                (second, (1980, 1, 1, 0, 0, 0)),
            ):
                with zipfile.ZipFile(path, "w") as archive:
                    info = zipfile.ZipInfo("package/module.py", timestamp)
                    info.external_attr = 0o100644 << 16
                    archive.writestr(info, b"VALUE = 1\n")

            first_fingerprint, _ = _normalized_wheel_manifest(first)
            second_fingerprint, _ = _normalized_wheel_manifest(second)

        self.assertEqual(first_fingerprint, second_fingerprint)


if __name__ == "__main__":
    unittest.main()
