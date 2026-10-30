#!/usr/bin/env python3
"""Exercise additive migration compatibility with a legacy SQLite writer."""

import argparse
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, Optional, Sequence


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_partial_state_benchmark import (
    ADDITIONS,
    _create_legacy_database,
)
from skill_runtime_intelligence.storage import Storage


MIGRATOR = (
    "import sys\n"
    "from pathlib import Path\n"
    "from skill_runtime_intelligence.storage import Storage\n"
    "storage = Storage(Path(sys.argv[1]))\n"
    "storage.close()\n"
)

LEGACY_INSERT = """
    INSERT INTO normalized_events (
        event_id, session_id, occurred_at, event_type, stage, status,
        evidence_grade, confidence, basis, summary, source_locator,
        payload_json
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def _migrator(database: Path) -> subprocess.Popen:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
    return subprocess.Popen(
        [sys.executable, "-c", MIGRATOR, str(database)],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _insert_legacy_row(
    connection: sqlite3.Connection,
    event_id: str,
) -> None:
    connection.execute(
        LEGACY_INSERT,
        (
            event_id,
            "legacy-session",
            "2026-07-30T07:00:00Z",
            "tool.completed",
            "execution",
            "observed",
            "observed",
            1.0,
            "controlled old-writer fixture",
            "Legacy writer event",
            f"fixture:{event_id}",
            "{}",
        ),
    )


def _inspect(database: Path, expected_events: int) -> Dict[str, Any]:
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
                   SUM(timestamp_origin = 'unknown') AS unknown_origins,
                   SUM(ingested_at IS NULL) AS null_ingested,
                   SUM(clock_domain = 'unknown') AS unknown_domains,
                   SUM(clock_uncertainty_ms IS NULL) AS null_uncertainty,
                   SUM(timestamp_precision = 'unknown') AS unknown_precision
            FROM normalized_events
            """
        ).fetchone()
        quick_check = str(
            connection.execute("PRAGMA quick_check").fetchone()[0]
        )
    finally:
        connection.close()
    complete_schema = all(column in columns for column, _ in ADDITIONS)
    legacy_defaults_preserved = all(
        int(row[field]) == expected_events
        for field in (
            "unknown_origins",
            "null_ingested",
            "unknown_domains",
            "null_uncertainty",
            "unknown_precision",
        )
    )
    passed = (
        complete_schema
        and int(row["event_count"]) == expected_events
        and legacy_defaults_preserved
        and quick_check == "ok"
    )
    return {
        "complete_schema": complete_schema,
        "event_count": int(row["event_count"]),
        "legacy_defaults_preserved": legacy_defaults_preserved,
        "quick_check": quick_check,
        "passed": passed,
    }


def _run_writer_before_case(
    database: Path,
    hold_seconds: float,
    expect_initial_success: bool,
) -> Dict[str, Any]:
    writer = sqlite3.connect(database)
    writer.execute("PRAGMA journal_mode = WAL")
    writer.execute("BEGIN IMMEDIATE")
    _insert_legacy_row(writer, "old-writer-before-migration")
    started = time.monotonic()
    migrator = _migrator(database)
    time.sleep(hold_seconds)
    writer.commit()
    writer.close()
    try:
        return_code = migrator.wait(timeout=8)
    except subprocess.TimeoutExpired:
        migrator.kill()
        return_code = migrator.wait(timeout=2)
    elapsed_ms = (time.monotonic() - started) * 1000

    recovery_succeeded = True
    try:
        recovered = Storage(database)
        recovered.close()
    except Exception:
        recovery_succeeded = False
    inspection = _inspect(database, expected_events=2)
    initial_behavior_correct = (
        return_code == 0 if expect_initial_success else return_code != 0
    )
    return {
        "schedule": (
            "writer_before_within_budget"
            if expect_initial_success
            else "writer_before_over_budget"
        ),
        "hold_seconds": hold_seconds,
        "initial_migration_success": return_code == 0,
        "recovery_succeeded": recovery_succeeded,
        "elapsed_ms": elapsed_ms,
        "inspection": inspection,
        "passed": (
            initial_behavior_correct
            and recovery_succeeded
            and inspection["passed"]
        ),
    }


def _run_writer_after_case(database: Path) -> Dict[str, Any]:
    storage = Storage(database)
    storage.close()
    writer = sqlite3.connect(database)
    try:
        _insert_legacy_row(writer, "old-writer-after-migration")
        writer.commit()
        legacy_write_succeeded = True
    except Exception:
        writer.rollback()
        legacy_write_succeeded = False
    finally:
        writer.close()
    inspection = _inspect(database, expected_events=2)
    return {
        "schedule": "writer_after_migration",
        "legacy_write_succeeded": legacy_write_succeeded,
        "inspection": inspection,
        "passed": legacy_write_succeeded and inspection["passed"],
    }


def run_benchmark(
    within_budget_holds: Sequence[float] = (0.05, 0.25),
    repetitions: int = 2,
    over_budget_hold: Optional[float] = 5.5,
) -> Dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(
        prefix="sri-old-writer-compatibility-"
    ) as directory:
        root = Path(directory)
        case_index = 0
        for hold_seconds in within_budget_holds:
            for _ in range(repetitions):
                database = root / f"before-{case_index}.db"
                case_index += 1
                _create_legacy_database(database, applied_prefix=0)
                results.append(
                    _run_writer_before_case(
                        database,
                        hold_seconds,
                        expect_initial_success=True,
                    )
                )
        for trial in range(repetitions):
            database = root / f"after-{trial}.db"
            _create_legacy_database(database, applied_prefix=0)
            results.append(_run_writer_after_case(database))
        if over_budget_hold is not None:
            database = root / "before-over-budget.db"
            _create_legacy_database(database, applied_prefix=0)
            results.append(
                _run_writer_before_case(
                    database,
                    over_budget_hold,
                    expect_initial_success=False,
                )
            )

    passed = sum(result["passed"] for result in results)
    schedule_counts: Dict[str, Dict[str, int]] = {}
    for result in results:
        summary = schedule_counts.setdefault(
            result["schedule"],
            {"evaluations": 0, "passed": 0},
        )
        summary["evaluations"] += 1
        summary["passed"] += int(result["passed"])
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.old-writer-compatibility.v1",
        "experiment": {
            "name": "timestamp-migration-old-writer-compatibility",
            "evidence_grade": "Experimental",
            "sqlite_busy_timeout_ms": 5000,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "The legacy writer is a raw SQLite fixture, not a packaged old binary.",
                "One writer and one migrator do not represent multi-writer workloads.",
                "Default-compatible inserts preserve unknown provenance but cannot add new timestamp provenance.",
                "Wall-clock lock holds are scheduler-sensitive.",
            ],
        },
        "environment": {
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
            "python_version": platform.python_version(),
            "sqlite_version": sqlite3.sqlite_version,
            "logical_cpu_count": os.cpu_count(),
            "load_average_1m": load[0],
            "load_average_5m": load[1],
            "load_average_15m": load[2],
        },
        "metrics": {
            "evaluations": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "by_schedule": schedule_counts,
            "all_old_writes_preserved": all(
                result["inspection"]["event_count"] == 2
                for result in results
            ),
            "all_old_writes_remain_unknown": all(
                result["inspection"]["legacy_defaults_preserved"]
                for result in results
            ),
        },
        "gate": {
            "name": "legacy writer preservation and bounded migration recovery",
            "passed": passed == len(results),
        },
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repetitions", type=int, default=2)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.repetitions < 1:
        parser.error("--repetitions must be >= 1")
    report = run_benchmark(repetitions=arguments.repetitions)
    output = write_report(
        EXPERIMENT_DIR,
        "old-writer-compatibility",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "environment": report["environment"],
                "metrics": report["metrics"],
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
