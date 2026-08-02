"""Compatibility packaging for Python environments with pre-PEP 660 pip."""

import re
from pathlib import Path

from setuptools import find_packages, setup


ROOT = Path(__file__).resolve().parent
README = (ROOT / "README.md").read_text(encoding="utf-8")
VERSION_MATCH = re.search(
    r'^__version__ = "([^"]+)"$',
    (ROOT / "src" / "skill_runtime_intelligence" / "__init__.py").read_text(
        encoding="utf-8"
    ),
    re.MULTILINE,
)
if VERSION_MATCH is None:
    raise RuntimeError("Unable to determine package version")


setup(
    name="skill-runtime-intelligence",
    version=VERSION_MATCH.group(1),
    description="Local-first, evidence-graded Agent Skill runtime intelligence",
    long_description=README,
    long_description_content_type="text/markdown",
    author="xueping",
    author_email="hellogxp@gmail.com",
    url="https://github.com/hellogxp/skill-runtime-intelligence",
    license="Apache-2.0",
    keywords="agent-skills observability diagnostics provenance local-first",
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Console",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Topic :: Software Development :: Debuggers",
    ],
    project_urls={
        "Documentation": "https://github.com/hellogxp/skill-runtime-intelligence#documentation",
        "Issues": "https://github.com/hellogxp/skill-runtime-intelligence/issues",
        "Releases": "https://github.com/hellogxp/skill-runtime-intelligence/releases",
        "Source": "https://github.com/hellogxp/skill-runtime-intelligence",
    },
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"skill_runtime_intelligence": ["web/*", "native/*"]},
    entry_points={
        "console_scripts": [
            "skill-runtime=skill_runtime_intelligence.cli:main",
            "skill-panorama=skill_runtime_intelligence.cli:main",
            "skill-runtime-hook=skill_runtime_intelligence.hook_cli:main",
        ]
    },
)
