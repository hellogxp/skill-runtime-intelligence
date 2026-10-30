import unittest

from experiments.run_suite import _summarize


class RunSuiteTests(unittest.TestCase):
    def test_environment_failure_does_not_hide_correctness_core(self):
        metrics = _summarize(
            [
                {
                    "gate_class": "correctness",
                    "passed": True,
                },
                {
                    "gate_class": "environment_sensitive",
                    "passed": False,
                },
            ]
        )

        self.assertEqual(metrics["experiment_count"], 2)
        self.assertEqual(metrics["passed"], 1)
        self.assertEqual(metrics["failed"], 1)
        self.assertTrue(metrics["correctness_core_passed"])
        self.assertEqual(
            metrics["by_gate_class"]["environment_sensitive"]["failed"],
            1,
        )


if __name__ == "__main__":
    unittest.main()
