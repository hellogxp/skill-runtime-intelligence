import unittest
from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "src" / "skill_runtime_intelligence" / "web"


class PanoramaViewportTests(unittest.TestCase):
    def test_dense_graph_focuses_the_lifecycle_spine_without_changing_graph_data(self):
        app = (WEB / "app.js").read_text(encoding="utf-8")
        styles = (WEB / "styles.css").read_text(encoding="utf-8")

        self.assertIn("function focusDagLifecycleSpine", app)
        self.assertIn("graphViewportRunId !== run.skill_run_id", app)
        self.assertIn("canvasHeight / 2 - 172", app)
        self.assertIn('focusDagLifecycleSpine("smooth")', app)
        self.assertIn("height: 344px; min-height: 344px; overflow: auto", styles)


if __name__ == "__main__":
    unittest.main()
