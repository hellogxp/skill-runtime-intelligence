#!/usr/bin/env python3
"""Kill a migration worker after each committed DDL boundary and recover."""

import argparse
import json
import os
import platform
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


def _kill_worker(database: Path, committed_prefix: int) -> int:
    worker = (
        "import os, signal, sqlite3, sys\n"
        f"additions = {ADDITIONS!r}\n"
        "database = sys.argv[1]\n"
        "cut = int(sys.argv[2])\n"
        "connection = sqlite3.connect(database)\n"
        "connection.execute('PRAGMA journal_mode = WAL')\n"
        "if cut == 0:\n"
        "    os.kill(os.getpid(), signal.SIGKILL)\n"
        "for index, (column, declaration) in enumerate(additions, start=1):\n"
        "    connection.execute(\n"
        "        f'ALTER TABLE normalized_events ADD COLUMN {column} {declaration}'\n"
        "    )\n"
        "    connection.commit()\n"
        "    if index == cut:\n"
        "        os.kill(os.getpid(), signal.SIGKILL)\n"
    )
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            worker,
            str(database),
            str(committed_prefix),
        ],
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
        prefix="sri-migration-kill-recovery-"
    ) as directory:
        root = Path(directory)
        for committed_prefix in range(len(ADDITIONS) + 1):
            for trial in range(trials):
                database = (
                    root / f"kill-{committed_prefix}-trial-{trial}.db"
                )
                _create_legacy_database(database, applied_prefix=0)
                worker_return_code = _kill_worker(
                    database,
                    committed_prefix,
                )
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
                    worker_return_code < 0
                    and all(column in columns for column, _ in ADDITIONS)
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
                        "committed_prefix": committed_prefix,
                        "trial": trial,
                        "worker_terminated_by_signal": worker_return_code < 0,
                        "passed": passed,
                    }
                )

    passed = sum(result["passed"] for result in results)
    kills = sum(
        result["worker_terminated_by_signal"] for result in results
    )
    passes_by_cut = {
        str(prefix): sum(
            result["passed"]
            for result in results
            if result["committed_prefix"] == prefix
        )
        for prefix in range(len(ADDITIONS) + 1)
    }
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.migration-kill-recovery.v1",
        "experiment": {
            "name": "timestamp-migration-process-kill-recovery",
            "evidence_grade": "Experimental",
            "kill_boundaries": len(ADDITIONS) + 1,
            "trials_per_boundary": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Kills occur after committed DDL boundaries, not inside SQLite atomic DDL.",
                "SIGKILL is not equivalent to power loss or filesystem corruption.",
                "The experiment covers one local OS, SQLite, and Python environment.",
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
            "workers_terminated_by_signal": kills,
            "passed": passed,
            "failed": len(results) - passed,
            "passes_by_committed_prefix": passes_by_cut,
            "legacy_unknown_preserved": passed == len(results),
            "idempotent_second_open": passed == len(results),
        },
        "gate": {
            "name": "all committed-boundary process kills recover",
            "passed": passed == len(results) and kills == len(results),
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
        "migration-kill-recovery",
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
