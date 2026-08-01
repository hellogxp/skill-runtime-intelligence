#!/usr/bin/env python3
"""Fail closed when public source or release assets contain internal material."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]

# Assemble markers so this policy file does not match itself. Keep the list
# intentionally narrow and high-confidence: these values identify private
# infrastructure, not ordinary uses of words such as "internal" in source code.
BLOCKED_CONTENT = (
    ("private Alibaba domain", b"alibaba" + b"-inc.com"),
    ("private Alipay domain", b"alipay" + b"-inc.com"),
    ("private Alipay domain", b"alipay" + b".com"),
    ("private ATA domain", b"ata" + b"tech.org"),
    ("private Yuque domain", b"ali" + b"yuque."),
    ("private Aliyun domain", b"aliyun" + b"-inc.com"),
    ("private proxy domain", b"intranet" + b"proxy."),
    ("private CLI distribution reference", b"cli" + b"-hub."),
    ("private distribution wording", b"Alibaba " + b"internal distribution"),
    ("private installation wording", b"internal installation " + b"guide"),
    ("private CLI distribution wording", b"Aone CLI " + b"Hub"),
)

BLOCKED_PATHS = {
    "/".join(("docs", "internal" + "-installation.md")),
    "/".join(("scripts", "install" + "-internal.sh")),
}


def _normalized_path(value: str) -> str:
    return PurePosixPath(value.replace("\\", "/")).as_posix().lstrip("./").lower()


def scan_path_name(label: str) -> list[str]:
    normalized = _normalized_path(label)
    if normalized in BLOCKED_PATHS or any(
        normalized.endswith(f"/{blocked}") for blocked in BLOCKED_PATHS
    ):
        return [f"{label}: private-only path is not allowed in the public repository"]
    return []


def scan_blob(label: str, payload: bytes) -> list[str]:
    lowered = payload.lower()
    findings = []
    for description, marker in BLOCKED_CONTENT:
        if marker.lower() in lowered:
            findings.append(f"{label}: contains {description}")
    return findings


def scan_archive(path: Path, label: str | None = None) -> list[str]:
    display = label or str(path)
    findings = scan_path_name(display)
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                for member in archive.infolist():
                    member_label = f"{display}!{member.filename}"
                    findings.extend(scan_path_name(member_label))
                    if not member.is_dir():
                        findings.extend(scan_blob(member_label, archive.read(member)))
            return findings
        if tarfile.is_tarfile(path):
            with tarfile.open(path, mode="r:*") as archive:
                for member in archive.getmembers():
                    member_label = f"{display}!{member.name}"
                    findings.extend(scan_path_name(member_label))
                    if member.isfile():
                        extracted = archive.extractfile(member)
                        if extracted is not None:
                            findings.extend(scan_blob(member_label, extracted.read()))
            return findings
        findings.extend(scan_blob(display, path.read_bytes()))
    except (OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        findings.append(f"{display}: could not be inspected: {error}")
    return findings


def tracked_files(root: Path) -> Iterable[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    for relative in result.stdout.decode("utf-8", errors="strict").split("\0"):
        if relative:
            yield root / relative


def scan_source_tree(root: Path) -> list[str]:
    findings = []
    for path in tracked_files(root):
        relative = path.relative_to(root).as_posix()
        findings.extend(scan_path_name(relative))
        if path.is_file():
            findings.extend(scan_blob(relative, path.read_bytes()))
    return findings


def scan_git_metadata(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "log", "--format=%H%x00%B%x00", "HEAD"],
        cwd=root,
        check=True,
        stdout=subprocess.PIPE,
    )
    return scan_blob("public commit history", result.stdout)


def scan_release_directory(directory: Path) -> list[str]:
    findings = []
    for path in sorted(directory.rglob("*")):
        if path.is_file():
            findings.extend(scan_archive(path, path.relative_to(directory).as_posix()))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--release-dir",
        type=Path,
        help="also inspect every release file and supported archive member",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="skip public commit-message inspection",
    )
    args = parser.parse_args()

    findings = scan_source_tree(REPOSITORY_ROOT)
    if not args.skip_history:
        findings.extend(scan_git_metadata(REPOSITORY_ROOT))
    if args.release_dir is not None:
        findings.extend(scan_release_directory(args.release_dir.resolve()))

    if findings:
        print("Public boundary check failed:", file=sys.stderr)
        for finding in sorted(set(findings)):
            print(f"- {finding}", file=sys.stderr)
        return 1
    print("Public boundary check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
