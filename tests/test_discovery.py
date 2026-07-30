import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_runtime_intelligence.discovery import (
    default_skill_roots,
    parse_skill,
)


class SkillDiscoveryTests(unittest.TestCase):
    def test_mainstream_agent_skill_roots_are_included(self):
        project = Path("/tmp/skill-runtime-project")
        roots = {str(path) for path in default_skill_roots(project)}
        self.assertIn(str(Path.home() / ".qoder" / "skills"), roots)
        self.assertIn(
            str(Path.home() / ".config" / "opencode" / "skills"), roots
        )
        self.assertIn(str(project / ".qoder" / "skills"), roots)
        self.assertIn(str(project / ".opencode" / "skills"), roots)

    def test_qoder_and_opencode_user_skills_are_not_labeled_project(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch(
                "skill_runtime_intelligence.discovery.Path.home",
                return_value=root,
            ):
                for relative in (
                    Path(".qoder/skills/demo/SKILL.md"),
                    Path(".config/opencode/skills/demo/SKILL.md"),
                ):
                    skill_file = root / relative
                    skill_file.parent.mkdir(parents=True, exist_ok=True)
                    skill_file.write_text(
                        "---\nname: demo\ndescription: demo skill\n---\n",
                        encoding="utf-8",
                    )
                    self.assertEqual(
                        parse_skill(skill_file).source_kind, "user"
                    )


if __name__ == "__main__":
    unittest.main()
