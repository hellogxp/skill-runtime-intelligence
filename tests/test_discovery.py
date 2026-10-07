import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from skill_runtime_intelligence.discovery import (
    default_skill_roots,
    discover_skills,
    parse_skill,
)


class SkillDiscoveryTests(unittest.TestCase):
    def test_discovers_a_skill_installed_as_a_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source" / "demo"
            source.mkdir(parents=True)
            (source / "SKILL.md").write_text(
                "---\nname: linked-demo\ndescription: linked skill\n---\n",
                encoding="utf-8",
            )
            installed = root / "installed"
            installed.mkdir()
            (installed / "linked-demo").symlink_to(source, target_is_directory=True)

            skills = discover_skills([installed])

            self.assertEqual([item.name for item in skills], ["linked-demo"])
            self.assertEqual(skills[0].source_path, str((source / "SKILL.md").resolve()))
    def test_mainstream_agent_skill_roots_are_included(self):
        project = Path("/tmp/skill-runtime-project")
        roots = {str(path) for path in default_skill_roots(project)}
        self.assertIn(str(Path.home() / ".qoder" / "skills"), roots)
        self.assertIn(str(Path.home() / ".qoderwork" / "skills"), roots)
        self.assertIn(
            str(Path.home() / ".config" / "opencode" / "skills"), roots
        )
        self.assertIn(str(project / ".qoder" / "skills"), roots)
        self.assertIn(str(project / ".qoderwork" / "skills"), roots)
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
                    Path(".qoderwork/skills/demo/SKILL.md"),
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
