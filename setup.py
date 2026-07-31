"""Compatibility packaging for Python environments with pre-PEP 660 pip."""

from setuptools import find_packages, setup


setup(
    name="skill-runtime-intelligence",
    version="0.2.1",
    description="Local-first, evidence-graded Agent Skill runtime intelligence",
    author="xueping",
    author_email="hellogxp@gmail.com",
    url="https://github.com/hellogxp/skill-runtime-intelligence",
    license="Apache-2.0",
    python_requires=">=3.9",
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
