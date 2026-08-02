#!/usr/bin/env python3
"""Import real pre-session failures as attempts, never as session outcomes."""

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.cross_agent.experiment_evidence_import_benchmark import (
    _session_index,
)
from experiments.cross_agent.experiment_evidence_schema_migration_benchmark import (
    _core_counts,
    _insert_task,
    _migrate,
)
from experiments.privacy_safe_paired_task_key import (
    ASSIGNMENT_SCHEMA,
    paired_task_key,
)
from experiments.real_corpus_audit.run_benchmark import _consistent_snapshot


DEFAULT_REPORTS = (
    REPOSITORY_ROOT
    / "experiments/live_agent/results/live-cross-agent-cli-20260731.json",
    REPOSITORY_ROOT
    / "experiments/live_agent/results/live-qoder-cli-20260731.json",
)
FAILURE_STATUSES = {"execution_error", "invalid_response"}


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _failure_rows(report_paths: Iterable[Path]) -> tuple:
    rows: List[Dict[str, Any]] = []
    task_digests = set()
    skill_digests = set()
    for path in report_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        task_digests.add(payload["experiment"]["task_sha256"])
        skill_digests.add(payload["experiment"]["skill_sha256"])
        report_digest = sha256_path(path)
        for trial in payload["trials"]:
            if trial["status"] not in FAILURE_STATUSES:
                continue
            verified = trial.get("outcome_verified")
            rows.append({
                "attempt_id": _digest("\0".join([
                    report_digest, trial["agent"], str(trial["trial"]),
                ])),
                "adapter": trial["agent"],
                "trial_index": trial["trial"],
                "attempt_status": trial["status"],
                "verifier_state": (
                    "failed" if verified is False else "not_run"
                ),
                "source_session_sha256": trial.get("session_id_sha256"),
                "source_report_sha256": report_digest,
            })
    if len(task_digests) != 1 or len(skill_digests) != 1:
        raise ValueError("reports do not share one task and Skill digest")
    return rows, task_digests.pop(), skill_digests.pop()


def _migrate_attempts(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE experimental_attempts (
            attempt_id TEXT PRIMARY KEY
                CHECK(length(attempt_id) = 64
                    AND attempt_id NOT GLOB '*[^0-9a-f]*'),
            task_key TEXT NOT NULL,
            adapter TEXT NOT NULL,
            trial_index INTEGER NOT NULL CHECK(trial_index > 0),
            attempt_status TEXT NOT NULL CHECK(attempt_status IN (
                'execution_error', 'invalid_response'
            )),
            verifier_state TEXT NOT NULL CHECK(verifier_state IN (
                'failed', 'not_run'
            )),
            session_id TEXT,
            source_session_sha256 TEXT
                CHECK(source_session_sha256 IS NULL OR (
                    length(source_session_sha256) = 64
                    AND source_session_sha256 NOT GLOB '*[^0-9a-f]*'
                )),
            resolution_state TEXT NOT NULL CHECK(resolution_state IN (
                'linked', 'unresolved'
            )),
            unresolved_reason TEXT CHECK(unresolved_reason IN (
                'source_session_absent', 'source_session_not_found',
                'source_session_ambiguous'
            )),
            evidence_grade TEXT NOT NULL CHECK(evidence_grade = 'Experimental'),
            source_report_sha256 TEXT NOT NULL
                CHECK(length(source_report_sha256) = 64
                    AND source_report_sha256 NOT GLOB '*[^0-9a-f]*'),
            imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_report_sha256, adapter, trial_index),
            FOREIGN KEY(task_key) REFERENCES experimental_tasks(task_key)
                ON DELETE CASCADE,
            FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                ON DELETE RESTRICT,
            CHECK(
                (resolution_state = 'linked'
                    AND session_id IS NOT NULL
                    AND source_session_sha256 IS NOT NULL
                    AND unresolved_reason IS NULL)
                OR
                (resolution_state = 'unresolved'
                    AND session_id IS NULL
                    AND unresolved_reason IS NOT NULL)
            )
        )
        """
    )


def _resolve(row: Dict[str, Any], session_index: Dict[str, list]) -> Dict[str, Any]:
    digest = row["source_session_sha256"]
    if digest is None:
        return {
            **row,
            "session_id": None,
            "resolution_state": "unresolved",
            "unresolved_reason": "source_session_absent",
        }
    candidates = session_index.get(digest, [])
    if len(candidates) == 1 and candidates[0]["adapter"] == row["adapter"]:
        return {
            **row,
            "session_id": candidates[0]["session_id"],
            "resolution_state": "linked",
            "unresolved_reason": None,
        }
    return {
        **row,
        "session_id": None,
        "resolution_state": "unresolved",
        "unresolved_reason": (
            "source_session_ambiguous" if len(candidates) > 1
            else "source_session_not_found"
        ),
    }


def _insert_attempt(
    connection: sqlite3.Connection,
    row: Dict[str, Any],
    task_key: str,
) -> str:
    values = (
        row["attempt_id"], task_key, row["adapter"], row["trial_index"],
        row["attempt_status"], row["verifier_state"], row["session_id"],
        row["source_session_sha256"], row["resolution_state"],
        row["unresolved_reason"], "Experimental", row["source_report_sha256"],
    )
    existing = connection.execute(
        "SELECT attempt_id, task_key, adapter, trial_index, attempt_status, "
        "verifier_state, session_id, source_session_sha256, resolution_state, "
        "unresolved_reason, evidence_grade, source_report_sha256 "
        "FROM experimental_attempts WHERE attempt_id = ?",
        (row["attempt_id"],),
    ).fetchone()
    if existing:
        if existing != values:
            raise ValueError("conflicting attempt evidence")
        return "idempotent"
    connection.execute(
        "INSERT INTO experimental_attempts(attempt_id, task_key, adapter, "
        "trial_index, attempt_status, verifier_state, session_id, "
        "source_session_sha256, resolution_state, unresolved_reason, "
        "evidence_grade, source_report_sha256) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        values,
    )
    return "inserted"


def run_benchmark(database: Path, report_paths: Iterable[Path]) -> Dict[str, Any]:
    rows, task_digest, skill_digest = _failure_rows(tuple(report_paths))
    snapshot, backup_attempts = _consistent_snapshot(database)
    try:
        connection = sqlite3.connect(snapshot)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            baseline_counts = _core_counts(connection)
            _migrate(connection)
            _migrate_attempts(connection)
            protocol = "installed-agent-black-box-v1"
            task_key = paired_task_key(
                snapshot.parent / "attempt-study.secret",
                {
                    "schema_version": ASSIGNMENT_SCHEMA,
                    "study_scope": "cross-agent-live-pilot-20260731",
                    "protocol_version": protocol,
                    "task_id": task_digest,
                },
            )["task_key"]
            _insert_task(connection, task_key, protocol)
            session_index = _session_index(snapshot)
            resolved = [_resolve(row, session_index) for row in rows]
            first = [_insert_attempt(connection, row, task_key) for row in resolved]
            second = [_insert_attempt(connection, row, task_key) for row in resolved]
            connection.commit()

            by_status = dict(connection.execute(
                "SELECT attempt_status, COUNT(*) FROM experimental_attempts "
                "GROUP BY attempt_status ORDER BY attempt_status"
            ).fetchall())
            by_verifier_state = dict(connection.execute(
                "SELECT verifier_state, COUNT(*) FROM experimental_attempts "
                "GROUP BY verifier_state ORDER BY verifier_state"
            ).fetchall())
            by_resolution = dict(connection.execute(
                "SELECT resolution_state, COUNT(*) FROM experimental_attempts "
                "GROUP BY resolution_state ORDER BY resolution_state"
            ).fetchall())
            outcome_count = connection.execute(
                "SELECT COUNT(*) FROM experimental_outcomes"
            ).fetchone()[0]

            connection.execute("SAVEPOINT invalid_resolution")
            inconsistent_resolution_rejected = False
            try:
                invalid = dict(resolved[0])
                invalid["attempt_id"] = "f" * 64
                invalid["resolution_state"] = "linked"
                invalid["unresolved_reason"] = None
                _insert_attempt(connection, invalid, task_key)
            except sqlite3.IntegrityError:
                inconsistent_resolution_rejected = True
            connection.execute("ROLLBACK TO invalid_resolution")
            connection.execute("RELEASE invalid_resolution")

            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            core_counts_preserved = baseline_counts == _core_counts(connection)
            connection.execute("DROP TABLE experimental_attempts")
            connection.execute("DROP TABLE experimental_outcomes")
            connection.execute("DROP TABLE experimental_tasks")
            connection.commit()
            downgrade_preserved = baseline_counts == _core_counts(connection)
        finally:
            connection.close()
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)
        (snapshot.parent / "attempt-study.secret").unlink(missing_ok=True)

    metrics = {
        "backup_attempts": backup_attempts,
        "real_failed_attempts": len(rows),
        "first_inserts": first.count("inserted"),
        "second_idempotent": second.count("idempotent"),
        "by_status": by_status,
        "by_verifier_state": by_verifier_state,
        "by_resolution": by_resolution,
        "session_outcomes_created_from_unresolved_attempts": outcome_count,
        "inconsistent_resolution_rejected": inconsistent_resolution_rejected,
        "core_counts_preserved": core_counts_preserved,
        "downgrade_preserved": downgrade_preserved,
        "integrity_check_ok": integrity == "ok",
    }
    passed = all([
        len(rows) == 5,
        metrics["first_inserts"] == 5,
        metrics["second_idempotent"] == 5,
        by_status == {"execution_error": 1, "invalid_response": 4},
        by_verifier_state == {"failed": 4, "not_run": 1},
        by_resolution == {"unresolved": 5},
        outcome_count == 0,
        inconsistent_resolution_rejected,
        core_counts_preserved,
        downgrade_preserved,
        integrity == "ok",
    ])
    return {
        "schema_version": "sri.experiment.attempt-failure-import.v1",
        "experiment": {
            "name": "real-pre-session-failure-attempt-import",
            "evidence_grade": "Experimental",
            "task_sha256": task_digest,
            "skill_sha256": skill_digest,
            "source_database_mutated_by_benchmark": False,
            "limitations": [
                "All writes occur on a consistent temporary database copy.",
                "The five failures come from one local machine and one study.",
                "Absent source-session identity prevents run-level attribution.",
                "Attempt records establish occurrence, not failure cause.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "Real failures remain attempts until session correlation exists",
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
        EXPERIMENT_DIR, "experiment-attempt-failure-import", report,
        arguments.output,
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
