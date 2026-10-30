#!/usr/bin/env python3
"""Exercise migration behavior under bounded and over-budget SQLite locks."""

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


WORKER = (
    "import sys\n"
    "from pathlib import Path\n"
    "from skill_runtime_intelligence.storage import Storage\n"
    "storage = Storage(Path(sys.argv[1]))\n"
    "storage.close()\n"
)


def _worker(database: Path) -> subprocess.Popen:
    environment = dict(os.environ)
    source_root = str(REPOSITORY_ROOT / "src")
    environment["PYTHONPATH"] = source_root
    return subprocess.Popen(
        [sys.executable, "-c", WORKER, str(database)],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _run_locked_case(
    database: Path,
    hold_seconds: float,
    expect_initial_success: bool,
) -> Dict[str, Any]:
    blocker = sqlite3.connect(database)
    blocker.execute("PRAGMA journal_mode = WAL")
    blocker.execute("PRAGMA busy_timeout = 5000")
    blocker.execute("BEGIN IMMEDIATE")
    blocker.execute(
        """
        UPDATE normalized_events
        SET summary = summary
        WHERE event_id = 'legacy-event'
        """
    )
    started = time.monotonic()
    worker = _worker(database)
    time.sleep(hold_seconds)
    blocker.commit()
    blocker.close()
    try:
        initial_return_code = worker.wait(timeout=8)
    except subprocess.TimeoutExpired:
        worker.kill()
        initial_return_code = worker.wait(timeout=2)
    elapsed_ms = (time.monotonic() - started) * 1000

    recovery_succeeded = True
    try:
        recovered = Storage(database)
        recovered.close()
    except Exception:
        recovery_succeeded = False

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
    initial_behavior_correct = (
        initial_return_code == 0
        if expect_initial_success
        else initial_return_code != 0
    )
    passed = (
        initial_behavior_correct
        and recovery_succeeded
        and all(column in columns for column, _ in ADDITIONS)
        and int(row["event_count"]) == 1
        and row["timestamp_origin"] == "unknown"
        and row["ingested_at"] is None
        and row["clock_domain"] == "unknown"
        and row["clock_uncertainty_ms"] is None
        and row["timestamp_precision"] == "unknown"
        and quick_check == "ok"
    )
    return {
        "hold_seconds": hold_seconds,
        "expect_initial_success": expect_initial_success,
        "initial_success": initial_return_code == 0,
        "recovery_succeeded": recovery_succeeded,
        "elapsed_ms": elapsed_ms,
        "passed": passed,
    }


def run_benchmark(
    within_budget_holds: Sequence[float] = (0.05, 0.25, 1.0),
    repetitions: int = 2,
    over_budget_hold: Optional[float] = 5.5,
) -> Dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(
        prefix="sri-migration-lock-contention-"
    ) as directory:
        root = Path(directory)
        case_index = 0
        for hold_seconds in within_budget_holds:
            for _ in range(repetitions):
                database = root / f"within-{case_index}.db"
                case_index += 1
                _create_legacy_database(database, applied_prefix=0)
                results.append(
                    _run_locked_case(
                        database,
                        hold_seconds,
                        expect_initial_success=True,
                    )
                )
        if over_budget_hold is not None:
            database = root / "over-budget.db"
            _create_legacy_database(database, applied_prefix=0)
            results.append(
                _run_locked_case(
                    database,
                    over_budget_hold,
                    expect_initial_success=False,
                )
            )

    passed = sum(result["passed"] for result in results)
    within = [item for item in results if item["expect_initial_success"]]
    over = [item for item in results if not item["expect_initial_success"]]
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.migration-lock-contention.v1",
        "experiment": {
            "name": "timestamp-migration-lock-contention",
            "evidence_grade": "Experimental",
            "sqlite_busy_timeout_ms": 5000,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Wall-clock lock holds are scheduler-sensitive.",
                "One writer lock does not represent all concurrent workload patterns.",
                "The experiment does not inject disk-full or I/O faults.",
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
            "within_budget_evaluations": len(within),
            "within_budget_initial_successes": sum(
                item["initial_success"] for item in within
            ),
            "over_budget_evaluations": len(over),
            "over_budget_initial_failures": sum(
                not item["initial_success"] for item in over
            ),
            "clean_recovery_successes": sum(
                item["recovery_succeeded"] for item in results
            ),
            "within_budget_elapsed_ms": [
                round(item["elapsed_ms"], 3) for item in within
            ],
            "over_budget_elapsed_ms": [
                round(item["elapsed_ms"], 3) for item in over
            ],
        },
        "gate": {
            "name": "lock-budget behavior and clean recovery",
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
        "migration-lock-contention",
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
