#!/usr/bin/env python3
"""Verify every published reproducibility artifact against its manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = REPOSITORY_ROOT / "reproducibility" / "manifest.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    arguments = parser.parse_args()
    manifest_path = arguments.manifest.resolve()
    repository_root = manifest_path.parent.parent
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures = []
    for record in manifest["files"]:
        path = repository_root / record["published_path"]
        if not path.is_file():
            failures.append(f"missing: {record['published_path']}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != record["published_sha256"]:
            failures.append(
                f"digest mismatch: {record['published_path']} "
                f"expected={record['published_sha256']} actual={actual}"
            )
    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(f"Verified {len(manifest['files'])} reproducibility artifacts.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
