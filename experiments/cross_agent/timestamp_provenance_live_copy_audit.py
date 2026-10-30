#!/usr/bin/env python3
"""Audit timestamp-provenance migration on a read-only live-database copy."""

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Set


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.storage import Storage


PROVENANCE_COLUMNS = {
    "timestamp_origin",
    "ingested_at",
    "clock_domain",
    "clock_uncertainty_ms",
    "timestamp_precision",
}


def _columns(connection: sqlite3.Connection) -> Set[str]:
    return {
        str(row["name"])
        for row in connection.execute(
            "PRAGMA table_info(normalized_events)"
        )
    }


def run_audit(database: Path) -> Dict[str, Any]:
    database = database.expanduser().resolve()
    with tempfile.TemporaryDirectory(
        prefix="sri-live-timestamp-copy-"
    ) as directory:
        snapshot = Path(directory) / "panorama.db"
        source = sqlite3.connect(
            f"file:{database}?mode=ro",
            uri=True,
        )
        destination = sqlite3.connect(snapshot)
        try:
            source.backup(destination)
        finally:
            source.close()
            destination.close()

        before = sqlite3.connect(snapshot)
        before.row_factory = sqlite3.Row
        try:
            before_columns = _columns(before)
            before_event_count = int(
                before.execute(
                    "SELECT COUNT(*) FROM normalized_events"
                ).fetchone()[0]
            )
            before_session_count = int(
                before.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )
        finally:
            before.close()

        migrated = Storage(snapshot)
        migrated.close()

        after = sqlite3.connect(snapshot)
        after.row_factory = sqlite3.Row
        try:
            after_columns = _columns(after)
            after_event_count = int(
                after.execute(
                    "SELECT COUNT(*) FROM normalized_events"
                ).fetchone()[0]
            )
            after_session_count = int(
                after.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )
            legacy = after.execute(
                """
                SELECT
                    SUM(CASE WHEN timestamp_origin = 'unknown' THEN 1 ELSE 0 END)
                        AS unknown_origin,
                    SUM(CASE WHEN ingested_at IS NULL THEN 1 ELSE 0 END)
                        AS null_ingested,
                    SUM(CASE WHEN clock_domain = 'unknown' THEN 1 ELSE 0 END)
                        AS unknown_domain,
                    SUM(CASE WHEN clock_uncertainty_ms IS NULL THEN 1 ELSE 0 END)
                        AS null_uncertainty,
                    SUM(CASE WHEN timestamp_precision = 'unknown' THEN 1 ELSE 0 END)
                        AS unknown_precision
                FROM normalized_events
                """
            ).fetchone()
            quick_check = str(after.execute("PRAGMA quick_check").fetchone()[0])
        finally:
            after.close()

    legacy_unknown = {
        key: int(legacy[key] or 0)
        for key in (
            "unknown_origin",
            "null_ingested",
            "unknown_domain",
            "null_uncertainty",
            "unknown_precision",
        )
    }
    gate_passed = (
        before_event_count == after_event_count
        and before_session_count == after_session_count
        and PROVENANCE_COLUMNS.issubset(after_columns)
        and quick_check == "ok"
    )
    report = {
        "schema_version": "sri.experiment.timestamp-provenance-live-copy.v1",
        "experiment": {
            "name": "read-only-live-copy-timestamp-provenance-migration",
            "evidence_grade": "Experimental",
            "source_open_mode": "read_only",
            "source_database_modified": False,
            "row_level_records_included": False,
            "limitations": [
                "An isolated database copy does not establish live deployment safety.",
                "Unknown legacy metadata is preserved rather than reconstructed.",
                "Aggregate migration integrity does not establish clock comparability.",
            ],
        },
        "metrics": {
            "event_count_before": before_event_count,
            "event_count_after": after_event_count,
            "session_count_before": before_session_count,
            "session_count_after": after_session_count,
            "provenance_columns_before": len(
                PROVENANCE_COLUMNS & before_columns
            ),
            "provenance_columns_after": len(
                PROVENANCE_COLUMNS & after_columns
            ),
            "legacy_unknown_or_null": legacy_unknown,
            "quick_check_ok": quick_check == "ok",
        },
        "gate": {
            "name": "isolated additive migration preserved aggregate identity",
            "passed": gate_passed,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"]["passed"] = gate_passed and privacy_passed
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database",
        type=Path,
        default=REPOSITORY_ROOT / ".sri" / "panorama.db",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_audit(arguments.database)
    output = write_report(
        EXPERIMENT_DIR,
        "timestamp-provenance-live-copy",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
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
