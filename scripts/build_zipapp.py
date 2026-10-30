#!/usr/bin/env python3
"""Build the dependency-free Skill Runtime CLI as a standalone zipapp."""

import argparse
import shutil
import stat
import tempfile
import zipapp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def build(output: Path) -> Path:
    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="skill-runtime-zipapp-") as directory:
        staging = Path(directory)
        shutil.copytree(
            ROOT / "src" / "skill_runtime_intelligence",
            staging / "skill_runtime_intelligence",
            ignore=shutil.ignore_patterns(
                "__pycache__",
                "*.pyc",
                "*.pyo",
                ".DS_Store",
            ),
        )
        (staging / "__main__.py").write_text(
            "from skill_runtime_intelligence.cli import main\nmain()\n",
            encoding="utf-8",
        )
        zipapp.create_archive(
            staging,
            target=output,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    output.chmod(output.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "dist" / "skill-runtime.pyz",
    )
    args = parser.parse_args()
    print(build(args.output))


if __name__ == "__main__":
    main()
