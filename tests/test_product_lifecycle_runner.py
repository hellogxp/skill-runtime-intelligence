import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from experiments.product_lifecycle.run_benchmark import (
    recover_cleanup_ledger,
    write_cleanup_ledger,
)


class ProductLifecycleRunnerTests(unittest.TestCase):
    def test_cleanup_ledger_survives_disposable_runtime_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime_record = root / "disposable" / "runtime.json"
            runtime_record.parent.mkdir()
            runtime_record.write_text(
                json.dumps(
                    {
                        "version": "skill-runtime-process-v1",
                        "marker": "skill-runtime-intelligence",
                        "pid": 123,
                        "command": ["python", "-m", "skill_runtime_intelligence"],
                    }
                ),
                encoding="utf-8",
            )
            ledger = root / "durable" / "cleanup.json"

            write_cleanup_ledger(runtime_record, ledger)
            runtime_record.unlink()

            self.assertTrue(ledger.is_file())
            self.assertEqual(json.loads(ledger.read_text())["pid"], 123)

    @mock.patch(
        "experiments.product_lifecycle.run_benchmark._managed_process",
        return_value=False,
    )
    def test_recovery_does_not_signal_unverified_process(self, managed):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Path(directory) / "cleanup.json"
            ledger.write_text(
                '{"pid":123,"marker":"skill-runtime-intelligence"}',
                encoding="utf-8",
            )
            with mock.patch(
                "experiments.product_lifecycle.run_benchmark.os.kill"
            ) as kill:
                result = recover_cleanup_ledger(ledger)

            self.assertTrue(result["ledger_found"])
            self.assertFalse(result["verified_process_found"])
            self.assertFalse(result["terminated"])
            self.assertFalse(ledger.exists())
            kill.assert_not_called()
            managed.assert_called_once()


if __name__ == "__main__":
    unittest.main()
