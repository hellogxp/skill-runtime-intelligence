#!/usr/bin/env python3
"""Audit whether a local real-run database can support corpus construction."""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import sha256_path, write_report
from skill_runtime_intelligence.storage import Storage


def _counter(counter: Counter) -> Dict[str, int]:
    return {str(key): counter[key] for key in sorted(counter, key=str)}


def _finding_rows(counter: Counter) -> list:
    return [
        {
            "code": code,
            "stage": stage,
            "evidence_grade": grade,
            "run_count": count,
        }
        for (code, stage, grade), count in sorted(counter.items())
    ]


def _consistent_snapshot(
    database: Path,
    attempts: int = 3,
) -> Tuple[Path, int]:
    """Copy a live SQLite database through the backup API without writing it."""
    database = database.expanduser().resolve()
    if not database.is_file():
        raise FileNotFoundError(database)
    last_error = None
    for attempt in range(1, attempts + 1):
        descriptor, snapshot_name = tempfile.mkstemp(
            prefix="sri-corpus-audit-",
            suffix=".db",
        )
        os.close(descriptor)
        snapshot = Path(snapshot_name)
        source = sqlite3.connect(str(database), timeout=5)
        destination = sqlite3.connect(snapshot, timeout=5)
        try:
            source.execute("PRAGMA query_only = ON")
            source.backup(destination)
            return snapshot, attempt
        except sqlite3.OperationalError as error:
            last_error = error
            snapshot.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(0.1 * attempt)
        finally:
            destination.close()
            source.close()
    raise last_error or RuntimeError("SQLite snapshot failed")


def _canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _snapshot_manifest(
    snapshot: Path,
    metrics: Dict[str, Any],
    readiness: Dict[str, Any],
) -> Dict[str, Any]:
    """Fingerprint the exact temporary snapshot without exporting its rows."""
    connection = sqlite3.connect(snapshot, timeout=5)
    try:
        connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        integrity_check = str(
            connection.execute("PRAGMA integrity_check").fetchone()[0]
        )
        schema_rows = connection.execute(
            """
            SELECT type, name, tbl_name, sql
            FROM sqlite_master
            WHERE type IN ('table', 'index', 'view', 'trigger')
            ORDER BY type, name
            """
        ).fetchall()
    finally:
        connection.close()
    return {
        "snapshot_sha256": sha256_path(snapshot),
        "snapshot_bytes": snapshot.stat().st_size,
        "schema_sha256": _canonical_sha256(schema_rows),
        "privacy_safe_aggregate_sha256": _canonical_sha256(
            {"metrics": metrics, "readiness": readiness}
        ),
        "integrity_check": integrity_check,
        "row_level_content_in_report": False,
        "interpretation": (
            "Local linkable fingerprints for snapshot identity and aggregate "
            "comparison; they do not retain or reconstruct the source rows."
        ),
    }


def _aggregate(storage: Storage) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    runs = storage.list_skill_runs(limit=100_000)
    statuses = Counter()
    adapters = Counter()
    evidence_grades = Counter()
    activation_modes = Counter()
    completeness = Counter()
    finding_signatures = Counter()
    finding_combinations = Counter()
    event_types = Counter()
    event_stages = Counter()
    event_grades = Counter()
    stage_profiles = Counter()
    session_ids = set()
    skill_ids = set()
    observed_activation_runs = 0
    verified_outcome_runs = 0
    explicit_failed_event_runs = 0

    for run in runs:
        statuses[str(run.get("status") or "unknown")] += 1
        adapters[str(run.get("adapter") or "unknown")] += 1
        evidence_grades[str(run.get("evidence_grade") or "unknown")] += 1
        activation_modes[str(run.get("activation_mode") or "unknown")] += 1
        session_ids.add(run.get("session_id"))
        skill_ids.add(run.get("skill_id"))
        detail = storage.get_skill_run(run["skill_run_id"])
        if not detail:
            continue
        completeness[str(detail.get("session_completeness") or "unknown")] += 1
        stage_profiles[
            tuple(
                (str(stage.get("stage")), str(stage.get("status")))
                for stage in detail.get("stage_summary", [])
            )
        ] += 1
        signatures = {
            (
                str(finding.get("code")),
                str(finding.get("stage")),
                str(finding.get("evidence_grade")),
            )
            for finding in detail.get("findings", [])
        }
        finding_signatures.update(signatures)
        finding_combinations[tuple(sorted(signatures))] += 1

        owned_events = [
            event
            for event in detail.get("events", [])
            if not event.get("context_only")
        ]
        types = {str(event.get("event_type")) for event in owned_events}
        observed_activation_runs += "skill.activated" in types
        verified_outcome_runs += "outcome.verified" in types
        explicit_failed_event_runs += any(
            event.get("status") == "failed" for event in owned_events
        )
        for event in owned_events:
            event_types[str(event.get("event_type") or "unknown")] += 1
            event_stages[str(event.get("stage") or "unknown")] += 1
            event_grades[str(event.get("evidence_grade") or "unknown")] += 1

    runtime_failure_candidates = sum(
        count
        for (code, _, _), count in finding_signatures.items()
        if code == "runtime_failure"
    )
    finding_occurrence_count = sum(finding_signatures.values())
    signature_group_count = len(finding_signatures)
    dominant_signature_count = max(finding_signatures.values(), default=0)
    systematic_signatures = [
        {
            "code": code,
            "stage": stage,
            "evidence_grade": grade,
            "run_count": count,
            "run_coverage": count / len(runs) if runs else 0.0,
        }
        for (code, stage, grade), count in sorted(finding_signatures.items())
        if runs and count / len(runs) >= 0.8
    ]
    metrics = {
        "run_count": len(runs),
        "session_count": len(session_ids),
        "skill_definition_count": len(skill_ids),
        "adapter_count": len(adapters),
        "status_counts": _counter(statuses),
        "adapter_counts": _counter(adapters),
        "run_evidence_grade_counts": _counter(evidence_grades),
        "activation_mode_counts": _counter(activation_modes),
        "session_completeness_counts": _counter(completeness),
        "distinct_stage_profile_count": len(stage_profiles),
        "distinct_finding_signature_count": len(finding_signatures),
        "distinct_finding_combination_count": len(finding_combinations),
        "finding_occurrence_count": finding_occurrence_count,
        "dominant_finding_signature_run_coverage": (
            dominant_signature_count / len(runs) if runs else 0.0
        ),
        "systematic_finding_signatures_at_80pct": systematic_signatures,
        "adapter_signature_grouping_potential": {
            "run_level_finding_occurrences": finding_occurrence_count,
            "adapter_signature_groups": signature_group_count,
            "occurrences_per_group": (
                finding_occurrence_count / signature_group_count
                if signature_group_count
                else 0.0
            ),
            "candidate_reduction_fraction": (
                1 - signature_group_count / finding_occurrence_count
                if finding_occurrence_count
                else 0.0
            ),
            "interpretation": (
                "Derived grouping opportunity only; no human notification "
                "benefit has been measured."
            ),
        },
        "finding_signatures": _finding_rows(finding_signatures),
        "owned_event_type_counts": _counter(event_types),
        "owned_event_stage_counts": _counter(event_stages),
        "owned_event_evidence_grade_counts": _counter(event_grades),
        "runs_with_observed_activation_event": observed_activation_runs,
        "runs_with_verified_outcome_event": verified_outcome_runs,
        "runs_with_explicit_failed_event": explicit_failed_event_runs,
        "runtime_failure_candidate_count": runtime_failure_candidates,
        "human_reviewed_label_count": 0,
    }
    checks = [
        ("at_least_20_runs", len(runs) >= 20),
        ("at_least_two_adapters", len(adapters) >= 2),
        (
            "at_least_four_finding_signatures",
            len(finding_signatures) >= 4,
        ),
        (
            "at_least_two_runtime_failure_candidates",
            runtime_failure_candidates >= 2,
        ),
        (
            "at_least_two_observed_activation_runs",
            observed_activation_runs >= 2,
        ),
        (
            "at_least_two_verified_outcome_runs",
            verified_outcome_runs >= 2,
        ),
        ("at_least_20_human_reviewed_labels", False),
    ]
    readiness = {
        "exploratory_criteria": [
            {"name": name, "passed": passed} for name, passed in checks
        ],
        "passed_count": sum(passed for _, passed in checks),
        "criterion_count": len(checks),
        "corpus_ready_for_confirmatory_evaluation": all(
            passed for _, passed in checks
        ),
    }
    return metrics, readiness


def _contains_forbidden_row_data(value: Any) -> bool:
    forbidden = {
        "skill_run_id",
        "session_id",
        "skill_id",
        "skill_name",
        "description",
        "summary",
        "payload",
        "source_path",
        "source_locator",
        "cwd",
        "session_title",
        "started_at",
        "ended_at",
    }
    if isinstance(value, dict):
        return bool(forbidden & set(value)) or any(
            _contains_forbidden_row_data(item) for item in value.values()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_row_data(item) for item in value)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    snapshot, snapshot_attempts = _consistent_snapshot(arguments.database)
    try:
        storage = Storage(snapshot)
        try:
            metrics, readiness = _aggregate(storage)
        finally:
            storage.close()
        dataset_manifest = _snapshot_manifest(snapshot, metrics, readiness)
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)

    report = {
        "schema_version": "sri.experiment.real-corpus-readiness.v3",
        "experiment": {
            "name": "privacy-safe-real-run-corpus-readiness-audit",
            "evidence_grade": "Derived",
            "source_database_basename": arguments.database.name,
            "consistent_snapshot": True,
            "snapshot_backup_attempts": snapshot_attempts,
            "source_query_only_enforced": True,
            "source_opened_with_read_only_uri": False,
            "source_content_writes_performed": False,
            "sqlite_locking_sidecars_may_be_created": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Production findings are Derived candidates, not human gold labels.",
                "The database contains one local user's runs and is not a deployment sample.",
                "Readiness thresholds are exploratory and were not preregistered.",
                "Aggregate counts do not establish diagnosis usefulness or causal Skill effects.",
                "SQLite query_only prevents content writes, but opening a live WAL database may create locking sidecar files.",
            ],
        },
        "metrics": metrics,
        "readiness": readiness,
        "dataset_manifest": dataset_manifest,
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    aggregation_passed = metrics["run_count"] > 0
    snapshot_integrity_passed = (
        dataset_manifest["integrity_check"].lower() == "ok"
    )
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "privacy-safe aggregate audit completed",
        "passed": (
            privacy_passed
            and aggregation_passed
            and snapshot_integrity_passed
        ),
    }
    output = write_report(
        EXPERIMENT_DIR,
        "real-corpus-readiness",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": metrics,
                "readiness": readiness,
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
