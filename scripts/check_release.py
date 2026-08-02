#!/usr/bin/env python3
"""Fail closed when release metadata or repository state is inconsistent."""

import argparse
import re
import struct
import subprocess
import sys
from pathlib import Path
from typing import List
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / "src" / "skill_runtime_intelligence" / "__init__.py"


def _match(path: Path, pattern: str, label: str) -> str:
    match = re.search(pattern, path.read_text(encoding="utf-8"), re.MULTILINE)
    if match is None:
        raise ValueError(f"{label} is missing from {path.relative_to(ROOT)}")
    return match.group(1)


def _local_link_errors(path: Path) -> List[str]:
    errors: List[str] = []
    text = path.read_text(encoding="utf-8")
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
        clean = target.strip().split(maxsplit=1)[0].strip("<>")
        if not clean or clean.startswith(("#", "http://", "https://", "mailto:")):
            continue
        relative = unquote(clean.split("#", 1)[0].split("?", 1)[0])
        if relative and not (path.parent / relative).exists():
            errors.append(
                f"{path.relative_to(ROOT)} has a missing local link: {clean}"
            )
    return errors


def _png_size(path: Path) -> tuple:
    header = path.read_bytes()[:24]
    if len(header) != 24 or not header.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError(f"{path.relative_to(ROOT)} is not a PNG file")
    return struct.unpack(">II", header[16:24])


def validate_release(tag: str = "", require_clean: bool = False) -> List[str]:
    version = _match(VERSION_FILE, r'^__version__ = "([^"]+)"$', "version")
    expected_tag = f"v{version}"
    errors: List[str] = []

    setup_version = subprocess.run(
        [sys.executable, "setup.py", "--version"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if setup_version != version:
        errors.append(f"package metadata is {setup_version}; expected {version}")

    citation_version = _match(
        ROOT / "CITATION.cff", r'^version: "([^"]+)"$', "citation version"
    )
    if citation_version != version:
        errors.append(
            f"CITATION.cff is {citation_version}; expected {version}"
        )

    metadata_files = [ROOT / "README.md", ROOT / "README.zh-CN.md"]
    metadata_files.extend(sorted(ROOT.glob("README.*.md")))
    metadata_files.append(ROOT / "CHANGELOG.md")
    for path in metadata_files:
        text = path.read_text(encoding="utf-8")
        if expected_tag not in text:
            errors.append(f"{path.relative_to(ROOT)} does not mention {expected_tag}")

    if tag and tag != expected_tag:
        errors.append(f"release tag is {tag}; expected {expected_tag}")

    required = (
        "LICENSE",
        "SECURITY.md",
        "CONTRIBUTING.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
        "docs/assets/skill-run-panorama.png",
        "src/skill_runtime_intelligence/web/favicon.svg",
        f"docs/releases/{expected_tag}.md",
    )
    for relative in required:
        if not (ROOT / relative).is_file():
            errors.append(f"required release file is missing: {relative}")

    for path in (
        ROOT / "README.md",
        ROOT / "README.zh-CN.md",
        ROOT / f"docs/releases/{expected_tag}.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "SECURITY.md",
    ):
        errors.extend(_local_link_errors(path))

    screenshot = ROOT / "docs/assets/skill-run-panorama.png"
    if screenshot.is_file():
        try:
            width, height = _png_size(screenshot)
            if width < 1280 or height < 720:
                errors.append(
                    f"release screenshot is only {width}x{height}; expected at least 1280x720"
                )
        except ValueError as exc:
            errors.append(str(exc))

    if require_clean:
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        if dirty:
            errors.append("release checkout is not clean")

    if errors:
        raise ValueError("\n".join(errors))
    return [
        f"version={version}",
        f"tag={expected_tag}",
        "metadata=consistent",
        "community_files=present",
        "local_links=valid",
        "screenshot=valid_png",
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", default="")
    parser.add_argument("--require-clean", action="store_true")
    arguments = parser.parse_args()
    try:
        checks = validate_release(arguments.tag, arguments.require_clean)
    except (OSError, subprocess.CalledProcessError, ValueError) as exc:
        print(f"release check failed:\n{exc}", file=sys.stderr)
        return 1
    print("release check passed: " + ", ".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
