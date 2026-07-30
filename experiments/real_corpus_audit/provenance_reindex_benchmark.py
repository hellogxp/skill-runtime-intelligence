#!/usr/bin/env python3
"""Localize reindex drift by collection provenance on an isolated DB copy."""

import argparse
import json
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _consistent_snapshot,
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.config import load_config
from skill_runtime_intelligence.discovery import default_skill_roots
from skill_runtime_intelligence.indexer import (
    _eligible_source_mtimes,
    _source_watermark,
    index_local,
)


TABLE_QUERIES = {
    "sessions": "SELECT collection_mode, COUNT(*) FROM sessions GROUP BY 1",
    "raw_records": (
        "SELECT s.collection_mode, COUNT(*) "
        "FROM raw_source_records r JOIN sessions s USING(session_id) GROUP BY 1"
    ),
    "events": (
        "SELECT s.collection_mode, COUNT(*) "
        "FROM normalized_events e JOIN sessions s USING(session_id) GROUP BY 1"
    ),
    "skill_runs": (
        "SELECT s.collection_mode, COUNT(*) "
        "FROM skill_runs sr JOIN sessions s USING(session_id) GROUP BY 1"
    ),
    "relationships": (
        "SELECT s.collection_mode, COUNT(*) "
        "FROM derived_relationships dr JOIN sessions s USING(session_id) GROUP BY 1"
    ),
    "inferences": (
        "SELECT s.collection_mode, COUNT(*) "
        "FROM inferences i JOIN sessions s USING(session_id) GROUP BY 1"
    ),
}

CHECKPOINT_FIELDS = (
    "status",
    "epoch",
    "source_count",
    "processed_source_count",
    "changed_source_count",
    "removed_source_count",
    "failed_source_count",
    "late_arrival_count",
    "start_revision",
    "end_revision",
)


def _provenance_counts(database: Path) -> Dict[str, Dict[str, int]]:
    connection = sqlite3.connect(database)
    try:
        modes = {
            str(row[0])
            for row in connection.execute(
                "SELECT DISTINCT collection_mode FROM sessions"
            ).fetchall()
        }
        result = {
            mode: {name: 0 for name in TABLE_QUERIES}
            for mode in sorted(modes)
        }
        for name, query in TABLE_QUERIES.items():
            for mode, count in connection.execute(query).fetchall():
                result.setdefault(
                    str(mode),
                    {key: 0 for key in TABLE_QUERIES},
                )[name] = int(count)
        return result
    finally:
        connection.close()


def _delta(
    before: Dict[str, Dict[str, int]],
    after: Dict[str, Dict[str, int]],
) -> Dict[str, Dict[str, int]]:
    result = {}
    for mode in sorted(set(before) | set(after)):
        values = {}
        for name in TABLE_QUERIES:
            change = after.get(mode, {}).get(name, 0) - before.get(
                mode, {}
            ).get(name, 0)
            if change:
                values[name] = change
        if values:
            result[mode] = values
    return result


def _boundary_change_count(
    before: Dict[Path, int],
    after: Dict[Path, int],
) -> int:
    return sum(
        before.get(source) != after.get(source)
        for source in set(before) | set(after)
    )


def _checkpoint_state(database: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(database)
    try:
        row = connection.execute(
            "SELECT value FROM runtime_state WHERE key = ?",
            ("collection.codex.epoch",),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return {}
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return {}
    if not isinstance(value, dict):
        return {}
    return {
        field: value.get(field)
        for field in CHECKPOINT_FIELDS
        if field in value
    }


def _checkpoint_matches_source(
    database: Path,
    source_mtimes: Dict[Path, int],
) -> bool:
    connection = sqlite3.connect(database)
    try:
        row = connection.execute(
            "SELECT value FROM runtime_state WHERE key = ?",
            ("collection.codex.epoch",),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return False
    try:
        value = json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return False
    return (
        isinstance(value, dict)
        and value.get("source_watermark_sha256")
        == _source_watermark(source_mtimes)
    )


def _checkpoint_converged(state: Dict[str, Any]) -> bool:
    return (
        state.get("status") == "completed"
        and state.get("failed_source_count") == 0
        and state.get("late_arrival_count") == 0
        and isinstance(state.get("end_revision"), int)
    )


def _skill_roots(project: Path, config_path: Path) -> Iterable[Path]:
    roots = default_skill_roots(project)
    config = load_config(config_path)
    for configured_project in config.get("projects", []):
        roots.extend(default_skill_roots(Path(configured_project)))
    return roots


def run_experiment(
    database: Path,
    codex_sessions: Path,
    project: Path,
    config_path: Path,
) -> Dict[str, Any]:
    snapshot, backup_attempts = _consistent_snapshot(database)
    adapter = CodexAdapter(codex_sessions)
    config = load_config(config_path)
    exclusions = [
        Path(value).expanduser()
        for value in config.get("exclude_paths", [])
    ]
    try:
        with tempfile.TemporaryDirectory(
            prefix="sri-provenance-reindex-"
        ) as directory:
            working = Path(directory) / "working.db"
            shutil.copy2(snapshot, working)
            snapshot_checkpoint = _checkpoint_state(working)
            before = _provenance_counts(working)

            source_before_first = _eligible_source_mtimes(
                adapter,
                exclusions,
            )
            checkpoint_matches_source = _checkpoint_matches_source(
                working,
                source_before_first,
            )
            first_index = index_local(
                working,
                codex_sessions,
                _skill_roots(project, config_path),
                exclusions,
            )
            source_after_first = _eligible_source_mtimes(
                adapter,
                exclusions,
            )
            after_first = _provenance_counts(working)

            source_before_second = source_after_first
            second_index = index_local(
                working,
                codex_sessions,
                _skill_roots(project, config_path),
                exclusions,
            )
            source_after_second = _eligible_source_mtimes(
                adapter,
                exclusions,
            )
            after_second = _provenance_counts(working)
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)

    first_delta = _delta(before, after_first)
    second_delta = _delta(after_first, after_second)
    first_boundary_changes = _boundary_change_count(
        source_before_first,
        source_after_first,
    )
    second_boundary_changes = _boundary_change_count(
        source_before_second,
        source_after_second,
    )
    hook_first_delta = first_delta.get("official_hook", {})
    hook_second_delta = second_delta.get("official_hook", {})
    hook_preserved = not hook_first_delta and not hook_second_delta
    second_identifiable = second_boundary_changes == 0
    second_idempotent = second_identifiable and not second_delta
    snapshot_checkpoint_converged = _checkpoint_converged(
        snapshot_checkpoint
    )
    live_to_reindex_identifiable = (
        first_boundary_changes == 0
        and snapshot_checkpoint_converged
        and checkpoint_matches_source
    )
    live_to_reindex_stable = live_to_reindex_identifiable and not first_delta
    report = {
        "schema_version": "sri.experiment.provenance-reindex-drift.v1",
        "experiment": {
            "name": "privacy-safe-provenance-reindex-drift",
            "evidence_grade": "Experimental",
            "source_query_only_snapshot": True,
            "isolated_working_copy": True,
            "raw_source_copy_persisted": False,
            "row_level_records_included": False,
            "raw_content_included": False,
            "snapshot_backup_attempts": backup_attempts,
            "limitations": [
                "One local database and host do not estimate a field failure rate.",
                "Source changes during a reindex make that comparison non-identifiable.",
                "A live snapshot without a completed zero-late checkpoint "
                "makes its comparison with a full reindex non-identifiable.",
                "Aggregate deltas do not identify individual records.",
                "The experiment reads live transcripts but never modifies them.",
            ],
        },
        "metrics": {
            "source_count_before_first": len(source_before_first),
            "source_boundary_changes_first": first_boundary_changes,
            "source_boundary_changes_second": second_boundary_changes,
            "snapshot_checkpoint": snapshot_checkpoint,
            "snapshot_checkpoint_converged": snapshot_checkpoint_converged,
            "snapshot_checkpoint_matches_source_boundary": (
                checkpoint_matches_source
            ),
            "first_index_imported": first_index["imported"],
            "first_index_failed": first_index["failed"],
            "second_index_imported": second_index["imported"],
            "second_index_failed": second_index["failed"],
            "first_reindex_delta_by_provenance": first_delta,
            "second_reindex_delta_by_provenance": second_delta,
        },
        "gates": {
            "official_hook_preserved": {
                "identifiable": True,
                "passed": hook_preserved,
            },
            "live_snapshot_to_first_reindex_stable": {
                "identifiable": live_to_reindex_identifiable,
                "passed": live_to_reindex_stable,
            },
            "second_reindex_idempotent": {
                "identifiable": second_identifiable,
                "passed": second_idempotent,
            },
        },
        "gate": {
            "name": "provenance-localized reindex stability",
            "passed": hook_preserved and second_idempotent,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"]["passed"] = report["gate"]["passed"] and privacy_passed
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
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
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment(
        arguments.database,
        arguments.codex_sessions,
        arguments.project,
        arguments.config,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "provenance-reindex",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
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
