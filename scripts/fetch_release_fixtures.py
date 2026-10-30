#!/usr/bin/env python3
"""Download digest-pinned historical release fixtures for compatibility tests."""

import argparse
import hashlib
import json
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = (
    ROOT / "experiments" / "product_lifecycle" / "release_wheel_manifest_v0.1.json",
    ROOT / "experiments" / "product_lifecycle" / "release_sdist_manifest_v0.1.json",
)
MAX_BYTES = 20 * 1024 * 1024


def _entry(path: Path, version: str) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    matches = [
        item for item in payload.get("artifacts", [])
        if item.get("version") == version
    ]
    if len(matches) != 1:
        raise ValueError(f"{path.name} has no unique entry for {version}")
    return matches[0]


def _download(entry: Dict[str, Any], output: Path) -> Path:
    url = str(entry["url"])
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "github.com":
        raise ValueError(f"unsupported fixture origin: {url}")
    filename = str(entry["filename"])
    if Path(filename).name != filename:
        raise ValueError(f"unsafe fixture filename: {filename}")
    output.mkdir(parents=True, exist_ok=True)
    destination = output / filename
    digest = hashlib.sha256()
    size = 0
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "skill-runtime-release-fixture-fetcher/1"},
    )
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(dir=output, delete=False) as temporary:
            temporary_path = Path(temporary.name)
            with urllib.request.urlopen(request, timeout=60) as response:
                while True:
                    chunk = response.read(64 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError(f"fixture exceeds {MAX_BYTES} bytes")
                    digest.update(chunk)
                    temporary.write(chunk)
        if size != int(entry["bytes"]):
            raise ValueError(f"size mismatch for {filename}: {size}")
        if digest.hexdigest() != entry["sha256"]:
            raise ValueError(f"SHA-256 mismatch for {filename}")
        temporary_path.replace(destination)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise
    return destination


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist")
    arguments = parser.parse_args()
    for manifest in MANIFESTS:
        path = _download(_entry(manifest, arguments.version), arguments.output)
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
