#!/usr/bin/env python3
"""Verify read-only migration failure is non-destructive and recoverable."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


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


def _attempt_storage_open(database: Path) -> int:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(REPOSITORY_ROOT / "src")
    completed = subprocess.run(
        [sys.executable, "-c", WORKER, str(database)],
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
        timeout=10,
    )
    return completed.returncode


def run_benchmark(trials: int = 3) -> Dict[str, Any]:
    results = []
    with tempfile.TemporaryDirectory(
        prefix="sri-migration-readonly-recovery-"
    ) as directory:
        root = Path(directory)
        for trial in range(trials):
            case = root / f"case-{trial}"
            case.mkdir()
            database = case / "panorama.db"
            _create_legacy_database(database, applied_prefix=0)
            database.chmod(0o444)
            case.chmod(0o555)
            initial_return_code = _attempt_storage_open(database)
            case.chmod(0o755)
            database.chmod(0o644)

            before = sqlite3.connect(database)
            before.row_factory = sqlite3.Row
            try:
                before_columns = {
                    str(row["name"])
                    for row in before.execute(
                        "PRAGMA table_info(normalized_events)"
                    )
                }
                before_event_count = int(
                    before.execute(
                        "SELECT COUNT(*) FROM normalized_events"
                    ).fetchone()[0]
                )
                before_quick_check = str(
                    before.execute("PRAGMA quick_check").fetchone()[0]
                )
            finally:
                before.close()

            recovery_succeeded = True
            try:
                recovered = Storage(database)
                recovered.close()
            except Exception:
                recovery_succeeded = False

            after = sqlite3.connect(database)
            after.row_factory = sqlite3.Row
            try:
                after_columns = {
                    str(row["name"])
                    for row in after.execute(
                        "PRAGMA table_info(normalized_events)"
                    )
                }
                row = after.execute(
                    """
                    SELECT COUNT(*) AS event_count,
                           timestamp_origin, ingested_at, clock_domain,
                           clock_uncertainty_ms, timestamp_precision
                    FROM normalized_events
                    """
                ).fetchone()
                after_quick_check = str(
                    after.execute("PRAGMA quick_check").fetchone()[0]
                )
            finally:
                after.close()

            passed = (
                initial_return_code != 0
                and not any(
                    column in before_columns for column, _ in ADDITIONS
                )
                and before_event_count == 1
                and before_quick_check == "ok"
                and recovery_succeeded
                and all(column in after_columns for column, _ in ADDITIONS)
                and int(row["event_count"]) == 1
                and row["timestamp_origin"] == "unknown"
                and row["ingested_at"] is None
                and row["clock_domain"] == "unknown"
                and row["clock_uncertainty_ms"] is None
                and row["timestamp_precision"] == "unknown"
                and after_quick_check == "ok"
            )
            results.append(
                {
                    "initial_readonly_failure": initial_return_code != 0,
                    "failed_attempt_left_schema_unchanged": not any(
                        column in before_columns for column, _ in ADDITIONS
                    ),
                    "recovery_succeeded": recovery_succeeded,
                    "passed": passed,
                }
            )

    passed = sum(result["passed"] for result in results)
    report = {
        "schema_version": "sri.experiment.migration-readonly-recovery.v1",
        "experiment": {
            "name": "timestamp-migration-readonly-recovery",
            "evidence_grade": "Experimental",
            "trials": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "POSIX permissions do not model every read-only filesystem.",
                "The experiment does not inject mid-write I/O failure.",
                "One local SQLite/Python environment is not cross-platform evidence.",
            ],
        },
        "metrics": {
            "evaluations": len(results),
            "initial_readonly_failures": sum(
                item["initial_readonly_failure"] for item in results
            ),
            "failed_attempts_schema_unchanged": sum(
                item["failed_attempt_left_schema_unchanged"]
                for item in results
            ),
            "clean_recovery_successes": sum(
                item["recovery_succeeded"] for item in results
            ),
            "passed": passed,
            "failed": len(results) - passed,
        },
        "gate": {
            "name": "read-only failure is non-destructive and recoverable",
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
        "migration-readonly-recovery",
        report,
        arguments.output,
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
