#!/usr/bin/env python3
"""Migrate databases created by three real repository history snapshots."""

import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, Sequence, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.product_lifecycle.migration_partial_state_benchmark import (
    ADDITIONS,
)
from skill_runtime_intelligence.storage import Storage


HISTORICAL_SNAPSHOTS: Sequence[Tuple[str, str]] = (
    ("bootstrap-panorama", "143d63b"),
    ("skill-run-core", "85f97a8"),
    ("release-v0.1.0", "5ab6252"),
)

HISTORICAL_BOOTSTRAP = (
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


def _git(*arguments: str, binary: bool = False):
    return subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
        text=not binary,
    ).stdout


def missing_historical_snapshots() -> Sequence[str]:
    """Return immutable experiment revisions absent from this checkout."""
    missing = []
    for label, revision in HISTORICAL_SNAPSHOTS:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{revision}^{{commit}}"],
            cwd=REPOSITORY_ROOT,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            missing.append(label)
    return tuple(missing)


def _snapshot_metadata(label: str, revision: str) -> Dict[str, str]:
    full_revision = _git("rev-parse", f"{revision}^{{commit}}").strip()
    fields = _git(
        "show",
        "-s",
        "--format=%cI%x00%s",
        full_revision,
    ).rstrip("\n").split("\x00", 1)
    return {
        "label": label,
        "requested_revision": revision,
        "revision": full_revision,
        "committed_at": fields[0],
        "subject": fields[1],
    }


def _extract_snapshot(revision: str, destination: Path) -> None:
    archive = _git("archive", "--format=tar", revision, binary=True)
    with tarfile.open(fileobj=BytesIO(archive), mode="r:") as bundle:
        destination_root = destination.resolve()
        for member in bundle.getmembers():
            target = (destination / member.name).resolve()
            if destination_root not in target.parents and target != destination_root:
                raise ValueError("historical archive contains an unsafe path")
        bundle.extractall(destination)


def _bootstrap_historical_database(source: Path, database: Path) -> None:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(source / "src")
    subprocess.run(
        [sys.executable, "-c", HISTORICAL_BOOTSTRAP, str(database)],
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )


def _schema_contract(database: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        tables = [
            str(row["name"])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                ORDER BY name
                """
            )
        ]
        columns = {}
        for table in tables:
            columns[table] = [
                {
                    "name": str(row["name"]),
                    "type": str(row["type"]),
                    "notnull": bool(row["notnull"]),
                    "default": row["dflt_value"],
                    "primary_key": bool(row["pk"]),
                }
                for row in connection.execute(f'PRAGMA table_info("{table}")')
            ]
    finally:
        connection.close()
    canonical = json.dumps(
        {"tables": tables, "columns": columns},
        sort_keys=True,
        separators=(",", ":"),
    )
    event_columns = {
        column["name"] for column in columns.get("normalized_events", [])
    }
    return {
        "fingerprint": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "table_count": len(tables),
        "has_skill_run_id": "skill_run_id" in event_columns,
        "has_runtime_state": "runtime_state" in tables,
        "provenance_columns_present": sum(
            column in event_columns for column, _ in ADDITIONS
        ),
    }


def _insert_legacy_event(database: Path, event_id: str) -> None:
    connection = sqlite3.connect(database)
    try:
        connection.execute(
            LEGACY_INSERT,
            (
                event_id,
                "historical-session",
                "2026-07-30T08:00:00Z",
                "session.started",
                "request",
                "observed",
                "observed",
                1.0,
                "controlled historical-contract fixture",
                "Historical contract event",
                f"fixture:{event_id}",
                "{}",
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _inspect_migrated(database: Path) -> Dict[str, Any]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        event_columns = {
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
    complete_schema = all(column in event_columns for column, _ in ADDITIONS)
    conservative_provenance = (
        row["timestamp_origin"] == "unknown"
        and row["ingested_at"] is None
        and row["clock_domain"] == "unknown"
        and row["clock_uncertainty_ms"] is None
        and row["timestamp_precision"] == "unknown"
    )
    passed = (
        complete_schema
        and int(row["event_count"]) == 1
        and conservative_provenance
        and quick_check == "ok"
    )
    return {
        "complete_schema": complete_schema,
        "event_count": int(row["event_count"]),
        "conservative_provenance": conservative_provenance,
        "quick_check": quick_check,
        "passed": passed,
    }


def run_benchmark(
    trials: int = 3,
    snapshots: Sequence[Tuple[str, str]] = HISTORICAL_SNAPSHOTS,
) -> Dict[str, Any]:
    snapshot_reports = []
    evaluations = []
    with tempfile.TemporaryDirectory(
        prefix="sri-historical-schema-contract-"
    ) as directory:
        root = Path(directory)
        for label, requested_revision in snapshots:
            metadata = _snapshot_metadata(label, requested_revision)
            source = root / label
            source.mkdir()
            _extract_snapshot(metadata["revision"], source)
            first_database = None
            contract = None
            for trial in range(trials):
                database = root / f"{label}-{trial}.db"
                _bootstrap_historical_database(source, database)
                before = _schema_contract(database)
                if contract is None:
                    contract = before
                    first_database = database
                _insert_legacy_event(database, f"{label}-event-{trial}")
                first = Storage(database)
                first.close()
                second = Storage(database)
                second.close()
                after = _inspect_migrated(database)
                passed = (
                    before["provenance_columns_present"] == 0
                    and after["passed"]
                )
                evaluations.append(
                    {
                        "label": label,
                        "trial": trial,
                        "historical_schema_fingerprint": before["fingerprint"],
                        "passed": passed,
                    }
                )
            assert contract is not None and first_database is not None
            snapshot_reports.append({**metadata, "schema_contract": contract})

    fingerprints = {
        snapshot["schema_contract"]["fingerprint"]
        for snapshot in snapshot_reports
    }
    passed = sum(item["passed"] for item in evaluations)
    load = os.getloadavg()
    report = {
        "schema_version": "sri.experiment.historical-schema-contract.v1",
        "experiment": {
            "name": "timestamp-migration-historical-schema-contract",
            "evidence_grade": "Experimental",
            "history_source": "local verified Git commit objects",
            "snapshot_count": len(snapshot_reports),
            "trials_per_snapshot": trials,
            "live_database_used": False,
            "row_level_records_included": False,
            "limitations": [
                "Historical source snapshots are executed directly, not installed from released wheels.",
                "Only three repository points and one controlled event shape are covered.",
                "The current working-tree migrator is evaluated on one local platform.",
                "This does not exercise concurrent writers or filesystem faults.",
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
        "snapshots": snapshot_reports,
        "metrics": {
            "evaluations": len(evaluations),
            "passed": passed,
            "failed": len(evaluations) - passed,
            "distinct_historical_schema_fingerprints": len(fingerprints),
            "snapshots_without_time_provenance": sum(
                snapshot["schema_contract"]["provenance_columns_present"] == 0
                for snapshot in snapshot_reports
            ),
            "legacy_events_preserved_as_unknown": passed == len(evaluations),
            "idempotent_second_open": passed == len(evaluations),
        },
        "gate": {
            "name": "all verified historical schema contracts migrate conservatively",
            "passed": (
                passed == len(evaluations)
                and len(fingerprints) == len(snapshot_reports)
            ),
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
        "historical-schema-contract",
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
