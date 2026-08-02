#!/usr/bin/env python3
"""Exercise recovery from every additive timestamp-migration prefix."""

import argparse
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from skill_runtime_intelligence.storage import Storage


ADDITIONS = (
    ("timestamp_origin", "TEXT NOT NULL DEFAULT 'unknown'"),
    ("ingested_at", "TEXT"),
    ("clock_domain", "TEXT NOT NULL DEFAULT 'unknown'"),
    ("clock_uncertainty_ms", "REAL"),
    ("timestamp_precision", "TEXT NOT NULL DEFAULT 'unknown'"),
)


def _create_legacy_database(path: Path, applied_prefix: int) -> None:
    connection = sqlite3.connect(path)
    connection.execute(
        """
        CREATE TABLE normalized_events (
            event_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            turn_id TEXT,
            skill_id TEXT,
            parent_event_id TEXT,
            occurred_at TEXT,
            event_type TEXT NOT NULL,
            stage TEXT NOT NULL,
            status TEXT NOT NULL,
            evidence_grade TEXT NOT NULL,
            confidence REAL NOT NULL,
            basis TEXT NOT NULL,
            summary TEXT NOT NULL,
            source_locator TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute(
        """
        INSERT INTO normalized_events (
            event_id, session_id, occurred_at, event_type, stage, status,
            evidence_grade, confidence, basis, summary, source_locator,
            payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-event",
            "legacy-session",
            "2026-07-30T06:00:00Z",
            "session.started",
            "request",
            "observed",
            "observed",
            1.0,
            "controlled legacy fixture",
            "Legacy event",
            "fixture:1",
            "{}",
        ),
    )
    for column, declaration in ADDITIONS[:applied_prefix]:
        connection.execute(
            f"ALTER TABLE normalized_events ADD COLUMN {column} {declaration}"
        )
    connection.commit()
    connection.close()


def run_benchmark(trials: int = 3) -> Dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(
        prefix="sri-partial-migration-matrix-"
    ) as directory:
        root = Path(directory)
        for applied_prefix in range(len(ADDITIONS) + 1):
            for trial in range(trials):
                database = root / f"prefix-{applied_prefix}-trial-{trial}.db"
                _create_legacy_database(database, applied_prefix)
                first = Storage(database)
                first.close()
                second = Storage(database)
                second.close()
                connection = sqlite3.connect(database)
                connection.row_factory = sqlite3.Row
                try:
                    columns = {
                        str(row["name"])
                        for row in connection.execute(
                            "PRAGMA table_info(normalized_events)"
                        )
                    }
                    row = connection.execute(
                        """
                        SELECT COUNT(*) AS event_count,
                               timestamp_origin, ingested_at, clock_domain,
                               clock_uncertainty_ms, timestamp_precision
                        FROM normalized_events
                        """
                    ).fetchone()
                    quick_check = str(
                        connection.execute("PRAGMA quick_check").fetchone()[0]
                    )
                finally:
                    connection.close()
                passed = (
                    all(column in columns for column, _ in ADDITIONS)
                    and int(row["event_count"]) == 1
                    and row["timestamp_origin"] == "unknown"
                    and row["ingested_at"] is None
                    and row["clock_domain"] == "unknown"
                    and row["clock_uncertainty_ms"] is None
                    and row["timestamp_precision"] == "unknown"
                    and quick_check == "ok"
                )
                results.append(
                    {
                        "applied_prefix": applied_prefix,
                        "trial": trial,
                        "passed": passed,
                    }
                )
    passed = sum(result["passed"] for result in results)
    prefix_passes = {
        str(prefix): sum(
            result["passed"]
            for result in results
            if result["applied_prefix"] == prefix
        )
        for prefix in range(len(ADDITIONS) + 1)
    }
    report = {
        "schema_version": "sri.experiment.partial-migration-matrix.v1",
        "experiment": {
            "name": "timestamp-additive-partial-migration-matrix",
            "evidence_grade": "Experimental",
            "migration_prefix_states": len(ADDITIONS) + 1,
            "trials_per_state": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Preconstructed partial states do not simulate process termination timing.",
                "The matrix covers additive prefixes, not arbitrary corruption.",
                "One SQLite/Python environment is not cross-platform evidence.",
            ],
        },
        "metrics": {
            "evaluations": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "passes_by_applied_prefix": prefix_passes,
            "legacy_unknown_preserved": passed == len(results),
            "idempotent_second_open": passed == len(results),
        },
        "gate": {
            "name": "all additive migration prefix states recover",
            "passed": passed == len(results),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials < 1:
        parser.error("--trials must be >= 1")
    report = run_benchmark(arguments.trials)
    output = write_report(
        EXPERIMENT_DIR,
        "partial-migration-matrix",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
