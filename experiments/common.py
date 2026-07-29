"""Shared, standard-library helpers for reproducible SRI experiments."""

import hashlib
import json
import os
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def git_value(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def environment() -> Dict[str, Any]:
    status = git_value("status", "--porcelain")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "git_commit": git_value("rev-parse", "HEAD"),
        "git_dirty": status not in {"", "unavailable"},
        "pai_dsw_instance_id": os.environ.get("PAI_DSW_INSTANCE_ID"),
        "experiment_root": os.environ.get("SRI_EXPERIMENT_ROOT"),
    }


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_jsonl(path: Path) -> list:
    rows = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
    if not rows:
        raise ValueError(f"No cases found in {path}")
    return rows


def percentile(values: Iterable[float], quantile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def write_report(
    experiment_dir: Path,
    prefix: str,
    report: Dict[str, Any],
    output: Path = None,
) -> Path:
    timestamp = utc_now()
    report.setdefault("created_at", timestamp.isoformat())
    report.setdefault("environment", environment())
    if output is None:
        output = (
            experiment_dir
            / "results"
            / f"{prefix}-{timestamp.strftime('%Y%m%dT%H%M%SZ')}.json"
        )
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return output

