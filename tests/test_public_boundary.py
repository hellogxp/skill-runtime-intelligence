import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "check_public_boundary.py"
SPEC = importlib.util.spec_from_file_location("check_public_boundary", SCRIPT_PATH)
assert SPEC and SPEC.loader
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


class PublicBoundaryTests(unittest.TestCase):
    def test_clean_public_content_passes(self):
        self.assertEqual(BOUNDARY.scan_blob("README.md", b"Public release docs"), [])

    def test_private_domain_is_rejected(self):
        marker = b"https://service." + b"alibaba" + b"-inc.com/path"
        findings = BOUNDARY.scan_blob("README.md", marker)
        self.assertTrue(any("private Alibaba domain" in item for item in findings))

    def test_private_only_path_is_rejected(self):
        path = "/".join(("docs", "internal" + "-installation.md"))
        self.assertTrue(BOUNDARY.scan_path_name(path))

    def test_embedded_archive_content_is_rejected(self):
        marker = b"https://service." + b"aliyun" + b"-inc.com/path"
        with tempfile.TemporaryDirectory() as directory:
            archive_path = Path(directory) / "release.zip"
            with zipfile.ZipFile(archive_path, "w") as archive:
                archive.writestr("docs/help.txt", marker)
            findings = BOUNDARY.scan_archive(archive_path)
        self.assertTrue(any("private Aliyun domain" in item for item in findings))

    def test_private_workspaces_are_rejected_in_source_and_archives(self):
        for path in (
            "paper/main.tex",
            "internal/notes.md",
            "competition-entry-example/proposal.pdf",
            "bundle.tar.gz!source/paper/main.tex",
            "bundle.zip!source/.sri/state.json",
        ):
            with self.subTest(path=path):
                self.assertTrue(BOUNDARY.scan_path_name(path))

    def test_benchmark_analysis_is_allowed(self):
        self.assertEqual(
            BOUNDARY.scan_path_name("experiments/paired_diagnostic_stats.py"), []
        )


if __name__ == "__main__":
    unittest.main()
