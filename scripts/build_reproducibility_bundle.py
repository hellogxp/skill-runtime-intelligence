#!/usr/bin/env python3
"""Build a privacy-safe, checksummed archive of experiment outputs.

The source result files remain untouched. Published copies replace only known
machine-local path prefixes and preserve every experimental metric and model
response. The manifest records both source and published SHA-256 digests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPOSITORY_ROOT / "reproducibility" / "results"
RESULT_SUFFIXES = {".json", ".jsonl"}
REPLACEMENTS = (
    (str(REPOSITORY_ROOT), "${REPO_ROOT}"),
    ("/Users/xueping.gxp", "${LOCAL_HOME}"),
    ("/mnt/workspace/sri-xueping/current", "${REPO_ROOT}"),
    ("/mnt/workspace/sri-xueping", "${PAI_WORKSPACE}"),
    ("/root/sri-xueping", "${PAI_HOME}"),
)


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _result_files() -> list[Path]:
    return sorted(
        path
        for path in (REPOSITORY_ROOT / "experiments").rglob("*")
        if path.is_file()
        and "results" in path.parts
        and path.suffix in RESULT_SUFFIXES
    )


def _sanitize(payload: bytes) -> tuple[bytes, int]:
    text = payload.decode("utf-8")
    replacement_count = 0
    for source, replacement in REPLACEMENTS:
        occurrences = text.count(source)
        if occurrences:
            text = text.replace(source, replacement)
            replacement_count += occurrences
    return text.encode("utf-8"), replacement_count


def build(output: Path) -> dict:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    records = []
    for source in _result_files():
        relative = source.relative_to(REPOSITORY_ROOT)
        destination = output / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        source_payload = source.read_bytes()
        published_payload, replacement_count = _sanitize(source_payload)
        destination.write_bytes(published_payload)
        records.append(
            {
                "source_path": relative.as_posix(),
                "source_sha256": _sha256(source_payload),
                "published_path": destination.relative_to(
                    REPOSITORY_ROOT
                ).as_posix(),
                "published_sha256": _sha256(published_payload),
                "bytes": len(published_payload),
                "path_replacements": replacement_count,
            }
        )
    manifest = {
        "schema_version": "sri.reproducibility-bundle.v1",
        "privacy_transform": {
            "scope": "known machine-local path prefixes only",
            "metrics_or_model_outputs_modified": False,
            "replacement_tokens": [replacement for _, replacement in REPLACEMENTS],
        },
        "file_count": len(records),
        "files": records,
    }
    manifest_path = output.parent / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    checksum_lines = [
        f"{record['published_sha256']}  {record['published_path']}"
        for record in records
    ]
    (output.parent / "CHECKSUMS.sha256").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    arguments = parser.parse_args()
    output = arguments.output.resolve()
    manifest = build(output)
    print(
        json.dumps(
            {
                "output": str(output),
                "file_count": manifest["file_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
