import unittest

from experiments.cross_agent.source_instance_contract_benchmark import (
    run_experiment,
)


class CrossAgentSourceContractTests(unittest.TestCase):
    def test_agent_scoped_identity_and_same_agent_append_contract(self):
        report = run_experiment(2)

        self.assertTrue(report["gate"]["passed"])
        self.assertEqual(report["metrics"]["exact_contract_trials"], 2)
        self.assertEqual(
            report["metrics"]["cross_agent_event_identity_collision_trials"],
            0,
        )
        self.assertEqual(
            report["metrics"]["cross_source_relationship_trials"],
            0,
        )
        self.assertNotIn("deliberately-shared", str(report))


if __name__ == "__main__":
    unittest.main()
