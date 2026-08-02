#!/usr/bin/env python3
"""Exercise Experimental task/outcome schema migration on a live DB copy."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.cross_agent.experiment_evidence_import_benchmark import (
    DEFAULT_REPORTS,
    _session_index,
    _verified_rows,
)
from experiments.live_agent.run_cross_agent_cli_trials import CANONICAL_SKILL
from experiments.privacy_safe_paired_task_key import (
    ASSIGNMENT_SCHEMA,
    SCHEME,
    paired_task_key,
)
from experiments.real_corpus_audit.run_benchmark import _consistent_snapshot


MIGRATION_VERSION = "experimental-evidence-v1"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _migrate(connection: sqlite3.Connection) -> None:
    statements = (
        """
        CREATE TABLE experimental_tasks (
            task_key TEXT PRIMARY KEY
                CHECK(length(task_key) = 41 AND task_key LIKE 'sri_task_%'),
            assignment_schema TEXT NOT NULL,
            scheme TEXT NOT NULL,
            protocol_version TEXT NOT NULL,
            evidence_grade TEXT NOT NULL CHECK(evidence_grade = 'Experimental'),
            assignment_basis TEXT NOT NULL CHECK(assignment_basis = 'explicit'),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """,
        """
        CREATE TABLE experimental_outcomes (
            outcome_id TEXT PRIMARY KEY,
            task_key TEXT NOT NULL,
            session_id TEXT NOT NULL,
            adapter TEXT NOT NULL,
            source_session_sha256 TEXT NOT NULL UNIQUE
                CHECK(length(source_session_sha256) = 64
                    AND source_session_sha256 NOT GLOB '*[^0-9a-f]*'),
            verifier_sha256 TEXT NOT NULL
                CHECK(length(verifier_sha256) = 64
                    AND verifier_sha256 NOT GLOB '*[^0-9a-f]*'),
            outcome_status TEXT NOT NULL CHECK(outcome_status IN (
                'verified_success', 'verified_failure', 'verification_error'
            )),
            evidence_grade TEXT NOT NULL CHECK(evidence_grade = 'Experimental'),
            source_report_sha256 TEXT NOT NULL
                CHECK(length(source_report_sha256) = 64
                    AND source_report_sha256 NOT GLOB '*[^0-9a-f]*'),
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(session_id, task_key, verifier_sha256),
            FOREIGN KEY(task_key) REFERENCES experimental_tasks(task_key)
                ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                ON DELETE RESTRICT
        )
        """,
        """
        CREATE INDEX idx_experimental_outcomes_task
            ON experimental_outcomes(task_key, adapter)
        """,
    )
    # Do not use executescript here: sqlite3 executescript() commits an active
    # transaction before running the script, which defeats migration rollback.
    for statement in statements:
        connection.execute(statement)


def _insert_task(
    connection: sqlite3.Connection,
    task_key: str,
    protocol_version: str,
) -> str:
    values = (
        task_key,
        ASSIGNMENT_SCHEMA,
        SCHEME,
        protocol_version,
        "Experimental",
        "explicit",
    )
    existing = connection.execute(
        "SELECT task_key, assignment_schema, scheme, protocol_version, "
        "evidence_grade, assignment_basis FROM experimental_tasks "
        "WHERE task_key = ?",
        (task_key,),
    ).fetchone()
    if existing:
        if existing != values:
            raise ValueError("conflicting task assignment")
        return "idempotent"
    connection.execute(
        "INSERT INTO experimental_tasks(task_key, assignment_schema, scheme, "
        "protocol_version, evidence_grade, assignment_basis) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        values,
    )
    return "inserted"


def _insert_outcome(
    connection: sqlite3.Connection,
    row: Dict[str, str],
    session_index: Dict[str, list],
    task_key: str,
    verifier_digest: str,
) -> str:
    candidates = session_index.get(row["source_session_sha256"], [])
    if len(candidates) != 1:
        raise ValueError("source session digest must resolve exactly once")
    session = candidates[0]
    if session["adapter"] != row["adapter"]:
        raise ValueError("adapter mismatch")
    outcome_id = _digest(
        "\0".join([session["session_id"], task_key, verifier_digest])
    )
    values = (
        outcome_id,
        task_key,
        session["session_id"],
        row["adapter"],
        row["source_session_sha256"],
        verifier_digest,
        row["outcome"],
        "Experimental",
        row["report_sha256"],
    )
    existing = connection.execute(
        "SELECT outcome_id, task_key, session_id, adapter, "
        "source_session_sha256, verifier_sha256, outcome_status, "
        "evidence_grade, source_report_sha256 FROM experimental_outcomes "
        "WHERE source_session_sha256 = ?",
        (row["source_session_sha256"],),
    ).fetchone()
    if existing:
        if existing != values:
            raise ValueError("conflicting outcome evidence")
        return "idempotent"
    connection.execute(
        "INSERT INTO experimental_outcomes(outcome_id, task_key, session_id, "
        "adapter, source_session_sha256, verifier_sha256, outcome_status, "
        "evidence_grade, source_report_sha256) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        values,
    )
    return "inserted"


def _core_counts(connection: sqlite3.Connection) -> Dict[str, int]:
    return {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("sessions", "raw_source_records", "normalized_events", "skill_runs")
    }


def run_benchmark(database: Path, report_paths: Iterable[Path]) -> Dict[str, Any]:
    report_paths = tuple(report_paths)
    rows, task_digest, skill_digest = _verified_rows(report_paths)
    snapshot, backup_attempts = _consistent_snapshot(database)
    try:
        connection = sqlite3.connect(snapshot)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            baseline_counts = _core_counts(connection)
            baseline_integrity = connection.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]

            connection.execute("BEGIN")
            try:
                _migrate(connection)
                connection.execute(
                    "INSERT INTO experimental_tasks(task_key, assignment_schema, "
                    "scheme, protocol_version, evidence_grade, assignment_basis) "
                    "VALUES ('invalid', ?, ?, 'v1', 'Experimental', 'explicit')",
                    (ASSIGNMENT_SCHEMA, SCHEME),
                )
            except sqlite3.IntegrityError:
                connection.rollback()
                failed_migration_rolled_back = True
            else:
                connection.rollback()
                failed_migration_rolled_back = False
            tables_after_rollback = {
                row[0] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }

            _migrate(connection)
            protocol = "installed-agent-black-box-v1"
            task_key = paired_task_key(
                snapshot.parent / "migration-study.secret",
                {
                    "schema_version": ASSIGNMENT_SCHEMA,
                    "study_scope": "cross-agent-live-pilot-20260731",
                    "protocol_version": protocol,
                    "task_id": task_digest,
                },
            )["task_key"]
            first_task = _insert_task(connection, task_key, protocol)
            second_task = _insert_task(connection, task_key, protocol)
            session_index = _session_index(snapshot)
            verifier_digest = sha256_path(
                CANONICAL_SKILL / "scripts" / "verify.py"
            )
            first_import = [
                _insert_outcome(
                    connection, row, session_index, task_key, verifier_digest
                )
                for row in rows
            ]
            second_import = [
                _insert_outcome(
                    connection, row, session_index, task_key, verifier_digest
                )
                for row in rows
            ]
            connection.commit()

            migrated_counts = _core_counts(connection)
            imported_by_adapter = dict(connection.execute(
                "SELECT adapter, COUNT(*) FROM experimental_outcomes "
                "GROUP BY adapter ORDER BY adapter"
            ).fetchall())

            connection.execute("SAVEPOINT contract_checks")
            invalid_verifier_rejected = False
            try:
                used_source_digests = {
                    row["source_session_sha256"] for row in rows
                }
                unused_digest, unused_candidates = next(
                    (digest, candidates)
                    for digest, candidates in session_index.items()
                    if len(candidates) == 1 and digest not in used_source_digests
                )
                invalid = dict(rows[0])
                invalid["source_session_sha256"] = unused_digest
                invalid["adapter"] = unused_candidates[0]["adapter"]
                _insert_outcome(
                    connection, invalid, session_index, task_key, "not-a-digest"
                )
            except sqlite3.IntegrityError as error:
                invalid_verifier_rejected = (
                    "verifier_sha256" in str(error)
                    or "CHECK constraint failed" in str(error)
                )
            except StopIteration:
                pass
            connection.execute("ROLLBACK TO contract_checks")
            connection.execute("RELEASE contract_checks")

            connection.execute("SAVEPOINT delete_contract")
            connection.execute(
                "DELETE FROM experimental_tasks WHERE task_key = ?", (task_key,)
            )
            cascade_deleted = connection.execute(
                "SELECT COUNT(*) FROM experimental_outcomes"
            ).fetchone()[0] == 0
            sessions_preserved_during_delete = (
                _core_counts(connection)["sessions"]
                == baseline_counts["sessions"]
            )
            connection.execute("ROLLBACK TO delete_contract")
            connection.execute("RELEASE delete_contract")

            post_migration_integrity = connection.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]
            connection.execute("DROP TABLE experimental_outcomes")
            connection.execute("DROP TABLE experimental_tasks")
            connection.commit()
            downgraded_counts = _core_counts(connection)
            downgraded_integrity = connection.execute(
                "PRAGMA quick_check"
            ).fetchone()[0]
            remaining_experimental_tables = connection.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' "
                "AND name LIKE 'experimental_%'"
            ).fetchone()[0]
        finally:
            connection.close()
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)
        secret = snapshot.parent / "migration-study.secret"
        secret.unlink(missing_ok=True)

    metrics = {
        "backup_attempts": backup_attempts,
        "verified_rows": len(rows),
        "failed_migration_rolled_back": failed_migration_rolled_back,
        "experimental_tables_absent_after_failed_migration": not bool(
            {"experimental_tasks", "experimental_outcomes"}
            & tables_after_rollback
        ),
        "task_first_inserted": first_task == "inserted",
        "task_second_idempotent": second_task == "idempotent",
        "outcome_first_inserts": first_import.count("inserted"),
        "outcome_second_idempotent": second_import.count("idempotent"),
        "imported_by_adapter": imported_by_adapter,
        "core_counts_preserved_after_migration": (
            baseline_counts == migrated_counts
        ),
        "invalid_verifier_rejected": invalid_verifier_rejected,
        "task_delete_cascades_outcomes": cascade_deleted,
        "task_delete_preserves_sessions": sessions_preserved_during_delete,
        "core_counts_preserved_after_downgrade": (
            baseline_counts == downgraded_counts
        ),
        "experimental_tables_absent_after_downgrade": (
            remaining_experimental_tables == 0
        ),
        "integrity_checks_ok": all(
            value == "ok" for value in (
                baseline_integrity,
                post_migration_integrity,
                downgraded_integrity,
            )
        ),
    }
    passed = all([
        len(rows) == 12,
        metrics["failed_migration_rolled_back"],
        metrics["experimental_tables_absent_after_failed_migration"],
        metrics["task_first_inserted"],
        metrics["task_second_idempotent"],
        metrics["outcome_first_inserts"] == 12,
        metrics["outcome_second_idempotent"] == 12,
        imported_by_adapter == {"codex": 4, "opencode": 4, "qoder": 4},
        metrics["core_counts_preserved_after_migration"],
        metrics["invalid_verifier_rejected"],
        metrics["task_delete_cascades_outcomes"],
        metrics["task_delete_preserves_sessions"],
        metrics["core_counts_preserved_after_downgrade"],
        metrics["experimental_tables_absent_after_downgrade"],
        metrics["integrity_checks_ok"],
    ])
    return {
        "schema_version": "sri.experiment.evidence-schema-migration.v1",
        "experiment": {
            "name": "live-copy-experimental-task-outcome-migration",
            "evidence_grade": "Experimental",
            "migration_version": MIGRATION_VERSION,
            "task_sha256": task_digest,
            "skill_sha256": skill_digest,
            "source_database_opened_via_consistent_backup": True,
            "source_database_mutated_by_benchmark": False,
            "limitations": [
                "All mutations occur on a temporary consistent copy.",
                "The live imported outcomes are successful fixture outcomes only.",
                "Failure-status acceptance is schema-covered but not a real failed run.",
                "User consent, concurrent production writers, UI, and release migration are untested.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "Experimental evidence migration is additive, idempotent, recoverable, and integrity-preserving",
            "passed": passed,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--reports", type=Path, nargs="+", default=DEFAULT_REPORTS)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_benchmark(arguments.database, arguments.reports)
    output = write_report(
        EXPERIMENT_DIR, "experiment-evidence-schema-migration", report,
        arguments.output,
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
