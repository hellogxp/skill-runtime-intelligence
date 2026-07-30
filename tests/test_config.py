import json
import tempfile
import unittest
from pathlib import Path

from skill_runtime_intelligence.config import load_config


class ConfigTests(unittest.TestCase):
    def test_existing_installation_gains_new_agent_consent_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text(
                json.dumps(
                    {
                        "projects": [],
                        "exclude_paths": [],
                        "hooks": {
                            "codex": {"consent": "granted"},
                        },
                    }
                ),
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config["hooks"]["codex"]["consent"], "granted")
            self.assertEqual(
                config["hooks"]["qoder"]["consent"], "not_requested"
            )
            self.assertEqual(
                config["hooks"]["opencode"]["consent"], "not_requested"
            )


if __name__ == "__main__":
    unittest.main()
