#!/usr/bin/env python3
"""Exercise packaged additive schema migration on a read-only live snapshot."""

import argparse
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Set


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)


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


def _run(command, environment, timeout=90) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            [str(part) for part in command],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
            timeout=timeout,
        )
        return {
            "return_code": completed.returncode,
            "stdout_bytes": len(completed.stdout.encode("utf-8")),
            "stderr_bytes": len(completed.stderr.encode("utf-8")),
        }
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "return_code": 124
            if isinstance(exc, subprocess.TimeoutExpired)
            else 127,
            "stdout_bytes": 0,
            "stderr_bytes": len(str(exc).encode("utf-8")),
        }


def run_audit(wheel: Path, database: Path) -> Dict[str, Any]:
    wheel = wheel.expanduser().resolve()
    database = database.expanduser().resolve()
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    with tempfile.TemporaryDirectory(
        prefix="sri-packaged-upgrade-migration-"
    ) as directory:
        root = Path(directory)
        snapshot = root / "panorama.db"
        virtualenv = root / "venv"

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
            before_events = int(
                before.execute(
                    "SELECT COUNT(*) FROM normalized_events"
                ).fetchone()[0]
            )
            before_sessions = int(
                before.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )
        finally:
            before.close()

        create_venv = _run(
            [sys.executable, "-m", "venv", virtualenv],
            environment,
        )
        python = virtualenv / "bin" / "python"
        install_wheel = _run(
            [
                python,
                "-m",
                "pip",
                "install",
                "--force-reinstall",
                "--no-index",
                "--no-deps",
                wheel,
            ],
            environment,
        )
        migration_code = (
            "import sys\n"
            "from pathlib import Path\n"
            "from skill_runtime_intelligence.storage import Storage\n"
            "path = Path(sys.argv[1])\n"
            "for _ in range(2):\n"
            "    storage = Storage(path)\n"
            "    storage.close()\n"
        )
        migrate_twice = _run(
            [python, "-c", migration_code, snapshot],
            environment,
        )

        after_migration = sqlite3.connect(snapshot)
        after_migration.row_factory = sqlite3.Row
        try:
            after_columns = _columns(after_migration)
            migrated_events = int(
                after_migration.execute(
                    "SELECT COUNT(*) FROM normalized_events"
                ).fetchone()[0]
            )
            migrated_sessions = int(
                after_migration.execute(
                    "SELECT COUNT(*) FROM sessions"
                ).fetchone()[0]
            )
            legacy = after_migration.execute(
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
            migration_quick_check = str(
                after_migration.execute("PRAGMA quick_check").fetchone()[0]
            )
        finally:
            after_migration.close()

        append_code = (
            "import sys\n"
            "from pathlib import Path\n"
            "from skill_runtime_intelligence.collector import "
            "normalize_collector_payload\n"
            "from skill_runtime_intelligence.storage import Storage\n"
            "event = {\n"
            "  'event_id': 'upgrade-migration-controlled-event',\n"
            "  'event_type': 'session.started',\n"
            "  'occurred_at': '2026-07-30T06:00:00Z',\n"
            "  'timestamp_origin': 'source',\n"
            "  'clock_domain': 'controlled_reference',\n"
            "  'clock_uncertainty_ms': 1.0,\n"
            "  'timestamp_precision': 'seconds',\n"
            "  'session_id': 'upgrade-migration-controlled-session',\n"
            "  'source': {\n"
            "    'adapter': 'migration-audit',\n"
            "    'adapter_version': '1',\n"
            "    'collection_mode': 'sdk'\n"
            "  }\n"
            "}\n"
            "storage = Storage(Path(sys.argv[1]))\n"
            "storage.append_collector_events(normalize_collector_payload(event))\n"
            "storage.close()\n"
        )
        append_controlled_event = _run(
            [python, "-c", append_code, snapshot],
            environment,
        )

        final = sqlite3.connect(snapshot)
        final.row_factory = sqlite3.Row
        try:
            final_events = int(
                final.execute(
                    "SELECT COUNT(*) FROM normalized_events"
                ).fetchone()[0]
            )
            final_sessions = int(
                final.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            )
            controlled = final.execute(
                """
                SELECT COUNT(*) AS event_count,
                       SUM(CASE
                           WHEN timestamp_origin = 'source'
                            AND ingested_at IS NOT NULL
                            AND clock_domain = 'controlled_reference'
                            AND clock_uncertainty_ms = 1.0
                            AND timestamp_precision = 'seconds'
                           THEN 1 ELSE 0
                       END) AS provenance_exact
                FROM normalized_events
                WHERE event_id = 'upgrade-migration-controlled-event'
                """
            ).fetchone()
            final_quick_check = str(
                final.execute("PRAGMA quick_check").fetchone()[0]
            )
        finally:
            final.close()

    steps = {
        "create_venv": create_venv,
        "install_wheel": install_wheel,
        "migrate_twice": migrate_twice,
        "append_controlled_event": append_controlled_event,
    }
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
        all(step["return_code"] == 0 for step in steps.values())
        and before_events == migrated_events
        and before_sessions == migrated_sessions
        and final_events == before_events + 1
        and final_sessions == before_sessions + 1
        and PROVENANCE_COLUMNS.issubset(after_columns)
        and int(controlled["event_count"]) == 1
        and int(controlled["provenance_exact"] or 0) == 1
        and migration_quick_check == "ok"
        and final_quick_check == "ok"
    )
    report = {
        "schema_version": "sri.experiment.packaged-upgrade-migration.v1",
        "experiment": {
            "name": "packaged-additive-upgrade-migration",
            "evidence_grade": "Experimental",
            "wheel": wheel.name,
            "offline_install": True,
            "source_database_open_mode": "read_only",
            "source_database_modified": False,
            "migration_repetitions": 2,
            "row_level_records_included": False,
            "limitations": [
                "One isolated snapshot does not establish live rollout safety.",
                "The experiment covers additive migration, not downgrade.",
                "Preserved aggregates do not establish timestamp accuracy.",
            ],
        },
        "metrics": {
            "step_return_codes": {
                name: step["return_code"] for name, step in steps.items()
            },
            "step_stdout_bytes": {
                name: step["stdout_bytes"] for name, step in steps.items()
            },
            "step_stderr_bytes": {
                name: step["stderr_bytes"] for name, step in steps.items()
            },
            "event_count_before": before_events,
            "event_count_after_migration": migrated_events,
            "event_count_after_controlled_append": final_events,
            "session_count_before": before_sessions,
            "session_count_after_migration": migrated_sessions,
            "session_count_after_controlled_append": final_sessions,
            "provenance_columns_before": len(
                PROVENANCE_COLUMNS & before_columns
            ),
            "provenance_columns_after": len(
                PROVENANCE_COLUMNS & after_columns
            ),
            "legacy_unknown_or_null": legacy_unknown,
            "controlled_event_persisted": int(controlled["event_count"]) == 1,
            "controlled_event_provenance_exact": (
                int(controlled["provenance_exact"] or 0) == 1
            ),
            "migration_quick_check_ok": migration_quick_check == "ok",
            "final_quick_check_ok": final_quick_check == "ok",
        },
        "gate": {
            "name": "packaged idempotent additive migration preserved aggregates",
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
    parser.add_argument("--wheel", type=Path, required=True)
    parser.add_argument(
        "--database",
        type=Path,
        default=REPOSITORY_ROOT / ".sri" / "panorama.db",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_audit(arguments.wheel, arguments.database)
    output = write_report(
        EXPERIMENT_DIR,
        "packaged-upgrade-migration",
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
