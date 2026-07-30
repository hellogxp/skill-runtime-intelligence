#!/usr/bin/env python3
"""Audit collection-checkpoint capabilities without exporting runtime rows."""

import argparse
import json
import sqlite3
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.real_corpus_audit.run_benchmark import (
    _consistent_snapshot,
    _contains_forbidden_row_data,
)


def _columns(connection: sqlite3.Connection, table: str) -> set:
    return {
        str(row[1])
        for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
    }


def _categorize_state_key(key: str) -> str:
    if key == "revision":
        return "global_revision"
    if key.startswith("export.otlp."):
        return "otlp_export"
    if key.startswith("collection.") and "epoch" in key:
        return "collection_epoch"
    if key.startswith("collection.") and "watermark" in key:
        return "collection_watermark"
    if key.startswith("collection.") and "late" in key:
        return "late_arrival"
    return "other"


def _audit_connection(connection: sqlite3.Connection) -> Dict[str, Any]:
    tables = {
        str(row[0])
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }
    runtime_columns = (
        _columns(connection, "runtime_state")
        if "runtime_state" in tables
        else set()
    )
    state_rows = (
        [
            (str(row[0]), str(row[1]))
            for row in connection.execute(
                "SELECT key, value FROM runtime_state ORDER BY key"
            ).fetchall()
        ]
        if "runtime_state" in tables
        else []
    )
    state_keys = [key for key, _ in state_rows]
    categories = Counter(_categorize_state_key(key) for key in state_keys)
    import_columns = (
        _columns(connection, "imports") if "imports" in tables else set()
    )
    session_columns = (
        _columns(connection, "sessions") if "sessions" in tables else set()
    )
    epoch_payloads = []
    for key, value in state_rows:
        if _categorize_state_key(key) != "collection_epoch":
            continue
        try:
            payload = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            epoch_payloads.append(payload)
    has_epoch_id = any(
        isinstance(payload.get("epoch"), int) for payload in epoch_payloads
    )
    has_epoch_status = any(
        payload.get("status") in {"running", "completed", "failed"}
        for payload in epoch_payloads
    )
    has_watermark = any(
        bool(payload.get("source_watermark_sha256"))
        for payload in epoch_payloads
    )
    has_late_arrival = any(
        isinstance(payload.get("late_arrival_count"), int)
        for payload in epoch_payloads
    )
    checks = [
        ("global_monotonic_revision", "revision" in state_keys),
        ("revision_update_timestamp", "updated_at" in runtime_columns),
        (
            "completed_import_digest",
            {"source_digest", "imported_at"} <= import_columns,
        ),
        ("collection_epoch_identifier", has_epoch_id),
        ("epoch_running_completed_state", has_epoch_status),
        ("source_high_watermark", has_watermark),
        ("late_arrival_counter", has_late_arrival),
    ]
    revision = 0
    if "revision" in state_keys:
        revision = int(
            connection.execute(
                "SELECT value FROM runtime_state WHERE key = 'revision'"
            ).fetchone()[0]
        )
    return {
        "schema_table_count": len(tables),
        "runtime_state_key_count": len(state_keys),
        "runtime_state_key_category_counts": {
            key: categories[key] for key in sorted(categories)
        },
        "current_global_revision": revision,
        "session_last_event_at_available": "last_event_at" in session_columns,
        "capabilities": [
            {"name": name, "available": available}
            for name, available in checks
        ],
        "available_capability_count": sum(
            available for _, available in checks
        ),
        "capability_count": len(checks),
        "freeze_checkpoint_available": all(
            available for _, available in checks[3:]
        ),
    }


def _cleanup(snapshot: Path) -> None:
    snapshot.unlink(missing_ok=True)
    Path(f"{snapshot}-wal").unlink(missing_ok=True)
    Path(f"{snapshot}-shm").unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    snapshot, attempts = _consistent_snapshot(arguments.database)
    try:
        connection = sqlite3.connect(snapshot)
        try:
            metrics = _audit_connection(connection)
            integrity_check = str(
                connection.execute("PRAGMA integrity_check").fetchone()[0]
            )
        finally:
            connection.close()
        snapshot_sha256 = sha256_path(snapshot)
    finally:
        _cleanup(snapshot)

    report = {
        "schema_version": "sri.experiment.collection-epoch-capability.v1",
        "experiment": {
            "name": "privacy-safe-collection-epoch-capability-audit",
            "evidence_grade": "Derived",
            "source_database_basename": arguments.database.name,
            "consistent_snapshot": True,
            "snapshot_backup_attempts": attempts,
            "source_query_only_enforced": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Schema availability does not prove checkpoint correctness.",
                "A global revision cannot delimit a multi-session watch batch.",
                "This audit does not estimate late-arrival frequency.",
            ],
        },
        "snapshot_manifest": {
            "snapshot_sha256": snapshot_sha256,
            "integrity_check": integrity_check,
        },
        "metrics": metrics,
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "collection checkpoint capabilities audited",
        "passed": privacy_passed and integrity_check.lower() == "ok",
    }
    output = write_report(
        EXPERIMENT_DIR,
        "collection-epoch-capability",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": metrics,
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
