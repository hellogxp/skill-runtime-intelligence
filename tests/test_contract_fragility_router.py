import unittest

from experiments.diagnostic_usefulness.analyze_contract_fragility_router import (
    authorization_fragility,
)


class ContractFragilityRouterTests(unittest.TestCase):
    def test_none_descriptive_is_maximally_fragile(self):
        self.assertEqual(
            authorization_fragility("none", "descriptive"), 1.0
        )

    def test_source_scope_allowed_kinds_are_partially_fragile(self):
        self.assertEqual(
            authorization_fragility(
                "source_assertion_only", "source_attribution"
            ),
            0.5,
        )

    def test_experimental_scope_is_not_fragile(self):
        self.assertEqual(
            authorization_fragility(
                "experimental_estimate", "skill_outcome_effect"
            ),
            0.0,
        )


if __name__ == "__main__":
    unittest.main()
