import tempfile
import unittest
from pathlib import Path

from experiments.live_agent.run_catalog_factorial import _contrast, _description, _prepare


class CatalogFactorialTests(unittest.TestCase):
    def test_overlap_and_length_are_independent(self):
        self.assertIn("checksum", _description(1, "short", "overlap"))
        self.assertNotIn("checksum", _description(1, "long", "disjoint"))
        self.assertGreater(len(_description(1, "long", "disjoint")), len(_description(1, "short", "disjoint")))

    def test_progressive_workspace_places_procedure_in_reference(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = _prepare(Path(directory), 0, 0, (8, "short", "disjoint", "progressive"))
            self.assertTrue(workspace.joinpath(".agents/skills/checksum-skill/references/procedure.md").exists())
            self.assertEqual(len(list(workspace.joinpath(".agents/skills").glob("distractor-*"))), 8)

    def test_contrast(self):
        rows = [{"factor": "low", "value": 2}, {"factor": "high", "value": 7}]
        self.assertEqual(_contrast(rows, "factor", "low", "high", "value")["high_minus_low_mean"], 5)


if __name__ == "__main__":
    unittest.main()
