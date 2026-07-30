#!/usr/bin/env python3
"""Measure reindex determinism on a frozen subset of historical transcripts."""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.config import load_config
from skill_runtime_intelligence.discovery import default_skill_roots
from skill_runtime_intelligence.indexer import index_local


GRAPH_TABLES = (
    "sessions",
    "raw_source_records",
    "normalized_events",
    "skill_runs",
    "derived_relationships",
    "inferences",
)
VOLATILE_COLUMNS = {"sessions": {"indexed_at"}}


def _select_historical_sources(
    adapter: CodexAdapter,
    *,
    now_ns: int,
    min_age_seconds: float,
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> List[Tuple[Path, int, int]]:
    candidates = []
    minimum_age_ns = int(min_age_seconds * 1_000_000_000)
    for source in adapter.session_files():
        try:
            stat = source.stat()
        except OSError:
            continue
        if now_ns - stat.st_mtime_ns < minimum_age_ns:
            continue
        if stat.st_size > max_file_bytes:
            continue
        candidates.append((source, stat.st_mtime_ns, stat.st_size))
    selected = []
    total_bytes = 0
    for candidate in sorted(candidates, key=lambda value: (value[1], str(value[0]))):
        if len(selected) >= max_files:
            break
        if total_bytes + candidate[2] > max_total_bytes:
            continue
        selected.append(candidate)
        total_bytes += candidate[2]
    return selected


def _copy_frozen_sources(
    selected: List[Tuple[Path, int, int]],
    source_root: Path,
    frozen_root: Path,
) -> Dict[str, int]:
    boundary_changes = 0
    copy_mismatches = 0
    copied_bytes = 0
    for source, expected_mtime_ns, expected_size in selected:
        try:
            relative = source.relative_to(source_root)
        except ValueError:
            boundary_changes += 1
            continue
        target = frozen_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        copied_bytes += target.stat().st_size
        try:
            after = source.stat()
        except OSError:
            boundary_changes += 1
            continue
        if (
            after.st_mtime_ns != expected_mtime_ns
            or after.st_size != expected_size
        ):
            boundary_changes += 1
            continue
        if _file_digest(source) != _file_digest(target):
            copy_mismatches += 1
    return {
        "source_boundary_changes_during_copy": boundary_changes,
        "copy_digest_mismatches": copy_mismatches,
        "copied_bytes": copied_bytes,
    }


def _file_digest(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_identity_profile(adapter: CodexAdapter) -> Dict[str, Any]:
    groups: Dict[str, List[Tuple[Path, List[bytes]]]] = defaultdict(list)
    missing_identity_files = 0
    for source in adapter.session_files():
        source_identity = ""
        line_hashes = []
        try:
            with source.open("rb") as handle:
                for line in handle:
                    line_hashes.append(hashlib.sha256(line).digest())
                    if source_identity:
                        continue
                    try:
                        record = json.loads(line)
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    if (
                        record.get("type") == "session_meta"
                        and isinstance(record.get("payload"), dict)
                    ):
                        payload = record["payload"]
                        source_identity = str(
                            payload.get("session_id")
                            or payload.get("id")
                            or ""
                        )
        except OSError:
            missing_identity_files += 1
            continue
        if not source_identity:
            missing_identity_files += 1
            source_identity = f"missing:{source}"
        groups[source_identity].append((source, line_hashes))

    multiplicities = Counter(len(files) for files in groups.values())
    duplicated_groups = [
        files for files in groups.values() if len(files) > 1
    ]
    divergent_groups = 0
    latest_contains_union_groups = 0
    unique_line_hashes = 0
    latest_line_hashes = 0
    unique_line_hashes_absent_from_latest = 0
    for files in duplicated_groups:
        files.sort(
            key=lambda value: (
                value[0].stat().st_mtime_ns,
                str(value[0]),
            )
        )
        sequences = [value[1] for value in files]
        if not all(
            sequences[index + 1][: len(sequences[index])]
            == sequences[index]
            for index in range(len(sequences) - 1)
        ):
            divergent_groups += 1
        union = set().union(*(set(sequence) for sequence in sequences))
        latest = set(sequences[-1])
        unique_line_hashes += len(union)
        latest_line_hashes += len(latest)
        absent = len(union - latest)
        unique_line_hashes_absent_from_latest += absent
        if absent == 0:
            latest_contains_union_groups += 1

    return {
        "source_files": sum(len(files) for files in groups.values()),
        "source_identity_count": len(groups),
        "missing_identity_files": missing_identity_files,
        "duplicate_identity_groups": len(duplicated_groups),
        "duplicate_identity_files": sum(
            len(files) - 1 for files in duplicated_groups
        ),
        "maximum_sources_per_identity": max(multiplicities, default=0),
        "identity_multiplicity_histogram": {
            str(multiplicity): count
            for multiplicity, count in sorted(multiplicities.items())
        },
        "divergent_duplicate_groups": divergent_groups,
        "latest_contains_union_groups": latest_contains_union_groups,
        "aggregate_unique_line_hashes_in_duplicate_groups": (
            unique_line_hashes
        ),
        "aggregate_latest_line_hashes_in_duplicate_groups": (
            latest_line_hashes
        ),
        "aggregate_unique_line_hashes_absent_from_latest": (
            unique_line_hashes_absent_from_latest
        ),
    }


def _table_fingerprints(database: Path) -> Dict[str, str]:
    connection = sqlite3.connect(database)
    try:
        result = {}
        for table in GRAPH_TABLES:
            info = connection.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
            columns = [
                str(row[1])
                for row in info
                if str(row[1]) not in VOLATILE_COLUMNS.get(table, set())
            ]
            primary_key = [
                str(row[1])
                for row in sorted(info, key=lambda row: int(row[5]) or 999)
                if int(row[5]) > 0
            ]
            query = "SELECT " + ", ".join(columns) + f" FROM {table}"
            if primary_key:
                query += " ORDER BY " + ", ".join(primary_key)
            digest = hashlib.sha256()
            for row in connection.execute(query):
                digest.update(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
                digest.update(b"\n")
            result[table] = digest.hexdigest()
        return result
    finally:
        connection.close()


def _table_counts(database: Path) -> Dict[str, int]:
    connection = sqlite3.connect(database)
    try:
        return {
            table: int(
                connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            )
            for table in GRAPH_TABLES
        }
    finally:
        connection.close()


def _skill_roots(project: Path, config_path: Path) -> Iterable[Path]:
    roots = default_skill_roots(project)
    config = load_config(config_path)
    for configured_project in config.get("projects", []):
        roots.extend(default_skill_roots(Path(configured_project)))
    return roots


def run_experiment(
    codex_sessions: Path,
    project: Path,
    config_path: Path,
    *,
    repeats: int,
    min_age_seconds: float,
    max_files: int,
    max_file_bytes: int,
    max_total_bytes: int,
) -> Dict[str, Any]:
    adapter = CodexAdapter(codex_sessions)
    selected = _select_historical_sources(
        adapter,
        now_ns=time.time_ns(),
        min_age_seconds=min_age_seconds,
        max_files=max_files,
        max_file_bytes=max_file_bytes,
        max_total_bytes=max_total_bytes,
    )
    config = load_config(config_path)
    exclusions = [
        Path(value).expanduser()
        for value in config.get("exclude_paths", [])
    ]
    repeat_results = []
    with tempfile.TemporaryDirectory(
        prefix="sri-frozen-corpus-"
    ) as directory:
        temporary_root = Path(directory)
        frozen_root = temporary_root / "sessions"
        copy_audit = _copy_frozen_sources(
            selected,
            codex_sessions,
            frozen_root,
        )
        identity_profile = _source_identity_profile(
            CodexAdapter(frozen_root)
        )
        database = temporary_root / "panorama.db"
        baseline_index = index_local(
            database,
            frozen_root,
            _skill_roots(project, config_path),
            exclusions,
        )
        baseline_counts = _table_counts(database)
        previous_fingerprints = _table_fingerprints(database)
        for repeat in range(1, repeats + 1):
            result = index_local(
                database,
                frozen_root,
                _skill_roots(project, config_path),
                exclusions,
            )
            counts = _table_counts(database)
            fingerprints = _table_fingerprints(database)
            repeat_results.append(
                {
                    "repeat": repeat,
                    "imported": result["imported"],
                    "failed": result["failed"],
                    "count_delta": {
                        table: counts[table] - baseline_counts[table]
                        for table in GRAPH_TABLES
                        if counts[table] != baseline_counts[table]
                    },
                    "table_fingerprint_equal_to_previous": {
                        table: (
                            fingerprints[table]
                            == previous_fingerprints[table]
                        )
                        for table in GRAPH_TABLES
                    },
                }
            )
            previous_fingerprints = fingerprints

    selected_count = len(selected)
    selected_bytes = sum(value[2] for value in selected)
    corpus_frozen = (
        selected_count > 0
        and copy_audit["source_boundary_changes_during_copy"] == 0
        and copy_audit["copy_digest_mismatches"] == 0
        and copy_audit["copied_bytes"] == selected_bytes
    )
    exact_repeats = sum(
        not result["count_delta"]
        and result["failed"] == 0
        and all(result["table_fingerprint_equal_to_previous"].values())
        for result in repeat_results
    )
    identity_safe = (
        identity_profile["missing_identity_files"] == 0
        and baseline_counts["sessions"] == selected_count
    )
    report = {
        "schema_version": "sri.experiment.frozen-corpus-reindex.v1",
        "experiment": {
            "name": "privacy-safe-frozen-historical-corpus-reindex",
            "evidence_grade": "Experimental",
            "adapter_version": adapter.version,
            "real_historical_transcripts": True,
            "temporary_raw_copy_deleted": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "fingerprint_values_included": False,
            "limitations": [
                "A bounded historical subset does not represent the full live corpus.",
                "Selection excludes active, oversized, and over-budget transcripts.",
                "One local host and adapter do not establish cross-Agent determinism.",
                "Fingerprint equality does not prove upstream source completeness.",
            ],
        },
        "selection": {
            "minimum_age_seconds": min_age_seconds,
            "maximum_files": max_files,
            "maximum_file_bytes": max_file_bytes,
            "maximum_total_bytes": max_total_bytes,
            "selected_files": selected_count,
            "selected_bytes": selected_bytes,
        },
        "copy_audit": copy_audit,
        "source_identity_profile": identity_profile,
        "metrics": {
            "baseline_imported": baseline_index["imported"],
            "baseline_failed": baseline_index["failed"],
            "baseline_counts": baseline_counts,
            "collapsed_source_instances": max(
                0,
                selected_count - baseline_counts["sessions"],
            ),
            "repeats_requested": repeats,
            "exact_repeat_count": exact_repeats,
            "repeat_results": repeat_results,
        },
        "gates": {
            "corpus_frozen": corpus_frozen,
            "baseline_import_clean": (
                baseline_index["failed"] == 0
                and baseline_index["imported"] == selected_count
            ),
            "all_repeats_exact": exact_repeats == repeats,
            "multi_source_identity_safe": identity_safe,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "frozen historical corpus reconstruction contract",
        "passed": (
            all(report["gates"].values())
            and privacy_passed
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codex-sessions",
        type=Path,
        default=Path("~/.codex/sessions").expanduser(),
    )
    parser.add_argument("--project", type=Path, default=Path.cwd())
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("~/.skill-runtime/config.json").expanduser(),
    )
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--min-age-seconds", type=float, default=3600)
    parser.add_argument("--max-files", type=int, default=12)
    parser.add_argument("--max-file-bytes", type=int, default=8 * 1024 * 1024)
    parser.add_argument("--max-total-bytes", type=int, default=64 * 1024 * 1024)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repeats < 1:
        parser.error("--repeats must be at least 1")
    if arguments.min_age_seconds < 0:
        parser.error("--min-age-seconds cannot be negative")
    if min(
        arguments.max_files,
        arguments.max_file_bytes,
        arguments.max_total_bytes,
    ) < 1:
        parser.error("file and byte limits must be positive")
    report = run_experiment(
        arguments.codex_sessions,
        arguments.project,
        arguments.config,
        repeats=arguments.repeats,
        min_age_seconds=arguments.min_age_seconds,
        max_files=arguments.max_files,
        max_file_bytes=arguments.max_file_bytes,
        max_total_bytes=arguments.max_total_bytes,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "frozen-corpus-reindex",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "selection": report["selection"],
                "copy_audit": report["copy_audit"],
                "source_identity_profile": report[
                    "source_identity_profile"
                ],
                "metrics": report["metrics"],
                "gates": report["gates"],
                "privacy_audit": report["privacy_audit"],
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
