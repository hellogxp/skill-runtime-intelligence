import tempfile
import unittest
from pathlib import Path

from experiments.real_corpus_audit.collection_epoch_benchmark import (
    _failure_trial,
    _new_source_trial,
    _trial,
    run_experiment,
)


class CollectionEpochBenchmarkTests(unittest.TestCase):
    def test_pair_distinguishes_injected_late_arrival(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            injected = _trial(
                root / "injected",
                inject_late_arrival=True,
            )
            control = _trial(
                root / "control",
                inject_late_arrival=False,
            )

        self.assertTrue(injected["running_seen"])
        self.assertTrue(injected["completed"])
        self.assertEqual(injected["late_arrival_count"], 1)
        self.assertTrue(injected["watermark_changed"])
        self.assertEqual(control["late_arrival_count"], 0)
        self.assertFalse(control["watermark_changed"])

    def test_failure_trial_persists_failed_epoch(self):
        with tempfile.TemporaryDirectory() as directory:
            result = _failure_trial(Path(directory) / "failure")

        self.assertTrue(result["running_seen"])
        self.assertTrue(result["failure_propagated"])
        self.assertTrue(result["failed"])
        self.assertEqual(result["failed_source_count"], 1)

    def test_new_source_inside_epoch_is_counted(self):
        with tempfile.TemporaryDirectory() as directory:
            result = _new_source_trial(Path(directory) / "new")

        self.assertTrue(result["running_seen"])
        self.assertTrue(result["completed"])
        self.assertEqual(result["late_arrival_count"], 1)

    def test_report_is_aggregate_and_passes(self):
        report = run_experiment(2, 1)

        self.assertTrue(report["gate"]["passed"])
        self.assertTrue(report["privacy_audit"]["passed"])
        self.assertEqual(report["metrics"]["detected_late_arrivals"], 2)
        self.assertEqual(report["metrics"]["detected_created_sources"], 2)
        self.assertNotIn("primary.jsonl", str(report))
        self.assertNotIn("controlled-session", str(report))


if __name__ == "__main__":
    unittest.main()
