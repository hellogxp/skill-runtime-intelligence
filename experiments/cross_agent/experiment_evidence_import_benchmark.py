#!/usr/bin/env python3
"""Link live verifier reports to sessions in an isolated evidence database."""

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.live_agent.run_cross_agent_cli_trials import CANONICAL_SKILL
from experiments.privacy_safe_paired_task_key import (
    ASSIGNMENT_SCHEMA,
    paired_task_key,
)


DEFAULT_REPORTS = (
    REPOSITORY_ROOT
    / "experiments/live_agent/results/live-cross-agent-cli-20260731.json",
    REPOSITORY_ROOT
    / "experiments/live_agent/results/live-qoder-cli-20260731.json",
    REPOSITORY_ROOT
    / "experiments/live_agent/results/live-qoder-cli-retry-20260731.json",
)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _verified_rows(report_paths: Iterable[Path]) -> tuple:
    rows: List[Dict[str, Any]] = []
    task_digests = set()
    skill_digests = set()
    for path in report_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        task_digests.add(payload["experiment"]["task_sha256"])
        skill_digests.add(payload["experiment"]["skill_sha256"])
        report_digest = sha256_path(path)
        for trial in payload["trials"]:
            if not trial.get("outcome_verified"):
                continue
            rows.append({
                "adapter": trial["agent"],
                "source_session_sha256": trial["session_id_sha256"],
                "report_sha256": report_digest,
                "outcome": "verified_success",
            })
    if len(task_digests) != 1 or len(skill_digests) != 1:
        raise ValueError("reports do not share one task and Skill digest")
    return rows, task_digests.pop(), skill_digests.pop()


def _session_index(database: Path) -> Dict[str, List[Dict[str, str]]]:
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT session_id, adapter, source_session_id FROM sessions "
            "WHERE source_session_id <> ''"
        ).fetchall()
    finally:
        connection.close()
    index: Dict[str, List[Dict[str, str]]] = {}
    for session_id, adapter, source_session_id in rows:
        index.setdefault(_digest(source_session_id), []).append({
            "session_id": session_id,
            "adapter": adapter,
        })
    return index


def _prepare_isolated_database(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE experimental_outcomes (
            outcome_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL UNIQUE,
            adapter TEXT NOT NULL,
            task_key TEXT NOT NULL,
            verifier_sha256 TEXT NOT NULL,
            outcome TEXT NOT NULL,
            evidence_grade TEXT NOT NULL,
            source_report_sha256 TEXT NOT NULL
        )
        """
    )


def _import_row(
    connection: sqlite3.Connection,
    row: Dict[str, str],
    session_index: Dict[str, List[Dict[str, str]]],
    task_key: str,
    verifier_digest: str,
) -> str:
    candidates = session_index.get(row["source_session_sha256"], [])
    if len(candidates) != 1:
        raise ValueError("source session digest must resolve exactly once")
    session = candidates[0]
    if session["adapter"] != row["adapter"]:
        raise ValueError("report adapter does not match linked session")
    values = {
        "outcome_id": _digest(
            "\0".join([session["session_id"], task_key, verifier_digest])
        ),
        "session_id": session["session_id"],
        "adapter": row["adapter"],
        "task_key": task_key,
        "verifier_sha256": verifier_digest,
        "outcome": row["outcome"],
        "evidence_grade": "Experimental",
        "source_report_sha256": row["report_sha256"],
    }
    existing = connection.execute(
        "SELECT outcome_id, adapter, task_key, verifier_sha256, outcome, "
        "evidence_grade, source_report_sha256 FROM experimental_outcomes "
        "WHERE session_id = ?",
        (values["session_id"],),
    ).fetchone()
    comparable = tuple(values[key] for key in (
        "outcome_id", "adapter", "task_key", "verifier_sha256", "outcome",
        "evidence_grade", "source_report_sha256",
    ))
    if existing:
        if existing != comparable:
            raise ValueError("conflicting evidence for linked session")
        return "idempotent"
    connection.execute(
        "INSERT INTO experimental_outcomes VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        tuple(values.values()),
    )
    return "inserted"


def run_benchmark(database: Path, report_paths: Iterable[Path]) -> Dict[str, Any]:
    report_paths = tuple(report_paths)
    rows, task_digest, skill_digest = _verified_rows(report_paths)
    session_index = _session_index(database)
    verifier_digest = sha256_path(CANONICAL_SKILL / "scripts" / "verify.py")
    with tempfile.TemporaryDirectory(
        prefix="sri-experiment-evidence-import-"
    ) as directory:
        root = Path(directory)
        task_key = paired_task_key(
            root / "study.secret",
            {
                "schema_version": ASSIGNMENT_SCHEMA,
                "study_scope": "cross-agent-live-pilot-20260731",
                "protocol_version": "installed-agent-black-box-v1",
                "task_id": task_digest,
            },
        )["task_key"]
        connection = sqlite3.connect(root / "isolated-evidence.db")
        try:
            _prepare_isolated_database(connection)
            first = [
                _import_row(
                    connection, row, session_index, task_key, verifier_digest
                )
                for row in rows
            ]
            second = [
                _import_row(
                    connection, row, session_index, task_key, verifier_digest
                )
                for row in rows
            ]
            wrong_digest = dict(rows[0], source_session_sha256="0" * 64)
            wrong_adapter = dict(rows[0], adapter="wrong-adapter")
            conflict = dict(rows[0], outcome="verified_failure")
            negatives = []
            for candidate in (wrong_digest, wrong_adapter, conflict):
                try:
                    _import_row(
                        connection,
                        candidate,
                        session_index,
                        task_key,
                        verifier_digest,
                    )
                    negatives.append(False)
                except ValueError:
                    negatives.append(True)
            stored = connection.execute(
                "SELECT adapter, COUNT(*) FROM experimental_outcomes "
                "GROUP BY adapter ORDER BY adapter"
            ).fetchall()
            stored_count = connection.execute(
                "SELECT COUNT(*) FROM experimental_outcomes"
            ).fetchone()[0]
        finally:
            connection.close()

    metrics = {
        "verified_report_rows": len(rows),
        "unique_source_session_digests": len({
            row["source_session_sha256"] for row in rows
        }),
        "exact_session_links": sum(
            len(session_index.get(row["source_session_sha256"], [])) == 1
            for row in rows
        ),
        "adapter_consistent_links": sum(
            len(session_index.get(row["source_session_sha256"], [])) == 1
            and session_index[row["source_session_sha256"]][0]["adapter"]
            == row["adapter"]
            for row in rows
        ),
        "first_import_inserts": first.count("inserted"),
        "second_import_idempotent": second.count("idempotent"),
        "stored_outcomes": stored_count,
        "stored_by_adapter": dict(stored),
        "negative_cases_rejected": sum(negatives),
        "negative_case_count": len(negatives),
    }
    passed = all([
        len(rows) == 12,
        metrics["unique_source_session_digests"] == 12,
        metrics["exact_session_links"] == 12,
        metrics["adapter_consistent_links"] == 12,
        metrics["first_import_inserts"] == 12,
        metrics["second_import_idempotent"] == 12,
        stored_count == 12,
        dict(stored) == {"codex": 4, "opencode": 4, "qoder": 4},
        all(negatives),
    ])
    return {
        "schema_version": "sri.experiment.evidence-import-linkage.v1",
        "experiment": {
            "name": "live-verifier-to-session-isolated-import",
            "evidence_grade": "Experimental",
            "source_report_count": len(report_paths),
            "task_sha256": task_digest,
            "skill_sha256": skill_digest,
            "verifier_sha256": verifier_digest,
            "production_database_mutated": False,
            "raw_prompt_exported": False,
            "source_session_id_exported": False,
            "limitations": [
                "The import target is an isolated temporary database.",
                "Digest linkage proves source identity, not semantic task equivalence.",
                "All outcomes are successful deterministic fixture results.",
                "Production schema, migration, UI, and user consent are untested.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "live outcomes link exactly and import safely in isolation",
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
        EXPERIMENT_DIR, "experiment-evidence-import", report, arguments.output
    )
    print(json.dumps({"metrics": report["metrics"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
