#!/usr/bin/env python3
"""Compare privacy-safe dataset cut policies on three live DB snapshots."""

import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.real_corpus_audit.run_benchmark import (
    _canonical_sha256,
    _consistent_snapshot,
    _contains_forbidden_row_data,
)


TERMINAL_STATUSES = {"completed", "failed", "interrupted"}


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _max_time(*values: Optional[str]) -> Optional[datetime]:
    parsed = [item for item in (_parse_time(value) for value in values) if item]
    return max(parsed) if parsed else None


def _load_private_states(snapshot: Path) -> Dict[str, Dict[str, Any]]:
    """Load row-level state for local matching; callers emit aggregates only."""
    connection = sqlite3.connect(snapshot)
    connection.row_factory = sqlite3.Row
    try:
        run_rows = connection.execute(
            """
            SELECT sr.skill_run_id, sr.run_index, sr.activation_mode,
                   sr.evidence_grade, sr.confidence, sr.status,
                   sr.started_at, sr.ended_at, sr.basis, sr.source_adapter,
                   sk.digest AS skill_digest,
                   s.adapter, s.adapter_version, s.source_format_version,
                   s.collection_mode, s.transport, s.source_health,
                   s.last_event_at, s.status AS session_status,
                   s.completeness AS session_completeness,
                   s.event_count AS session_event_count
            FROM skill_runs sr
            JOIN sessions s ON s.session_id = sr.session_id
            JOIN skills sk ON sk.skill_id = sr.skill_id
            """
        ).fetchall()
        event_rows = connection.execute(
            """
            SELECT skill_run_id, event_id, parent_event_id, occurred_at,
                   event_type, stage, status, evidence_grade, confidence, basis
            FROM normalized_events
            WHERE skill_run_id IS NOT NULL
            ORDER BY skill_run_id, occurred_at, event_id
            """
        ).fetchall()
        relationship_rows = connection.execute(
            """
            SELECT skill_run_id, relationship_id, source_event_id,
                   target_event_id, relationship_type, evidence_grade,
                   confidence, basis
            FROM derived_relationships
            WHERE skill_run_id IS NOT NULL
            ORDER BY skill_run_id, relationship_id
            """
        ).fetchall()
        integrity_check = str(
            connection.execute("PRAGMA integrity_check").fetchone()[0]
        )
    finally:
        connection.close()

    events: Dict[str, list] = {}
    event_times: Dict[str, list] = {}
    for row in event_rows:
        item = dict(row)
        run_id = item.pop("skill_run_id")
        events.setdefault(run_id, []).append(item)
        event_times.setdefault(run_id, []).append(item.get("occurred_at"))

    relationships: Dict[str, list] = {}
    for row in relationship_rows:
        item = dict(row)
        run_id = item.pop("skill_run_id")
        relationships.setdefault(run_id, []).append(item)

    states = {}
    for row in run_rows:
        item = dict(row)
        run_id = item.pop("skill_run_id")
        latest_at = _max_time(
            item.get("started_at"),
            item.get("ended_at"),
            item.get("last_event_at"),
            *event_times.get(run_id, []),
        )
        state = {
            "run": item,
            "events": events.get(run_id, []),
            "relationships": relationships.get(run_id, []),
        }
        states[run_id] = {
            "status": str(item.get("status") or "unknown"),
            "latest_at": latest_at,
            "fingerprint": _canonical_sha256(state),
            "integrity_check": integrity_check,
        }
    return states


def _score_selection(
    selected: Set[str],
    selection_states: Dict[str, Dict[str, Any]],
    outcome_states: Dict[str, Dict[str, Any]],
    total_at_selection: int,
) -> Dict[str, Any]:
    missing = selected - set(outcome_states)
    comparable = selected & set(outcome_states)
    changed = {
        run_id
        for run_id in comparable
        if selection_states[run_id]["fingerprint"]
        != outcome_states[run_id]["fingerprint"]
    }
    stable = comparable - changed
    selected_count = len(selected)
    return {
        "selected_run_count": selected_count,
        "selection_fraction": (
            selected_count / total_at_selection if total_at_selection else 0.0
        ),
        "stable_next_interval_count": len(stable),
        "changed_next_interval_count": len(changed),
        "missing_next_interval_count": len(missing),
        "stable_next_interval_fraction": (
            len(stable) / selected_count if selected_count else None
        ),
    }


def _evaluate_policies(
    before_states: Dict[str, Dict[str, Any]],
    selection_states: Dict[str, Dict[str, Any]],
    outcome_states: Dict[str, Dict[str, Any]],
    selection_captured_at: datetime,
    watermark_seconds: float,
    observed_quiescence_seconds: float,
) -> Dict[str, Any]:
    all_runs = set(selection_states)
    terminal_runs = {
        run_id
        for run_id, state in selection_states.items()
        if state["status"] in TERMINAL_STATUSES
    }
    watermark = selection_captured_at - timedelta(seconds=watermark_seconds)
    watermark_runs = {
        run_id
        for run_id, state in selection_states.items()
        if state["latest_at"] is not None and state["latest_at"] <= watermark
    }
    quiescent_runs = {
        run_id
        for run_id in set(before_states) & set(selection_states)
        if before_states[run_id]["fingerprint"]
        == selection_states[run_id]["fingerprint"]
    }
    total = len(selection_states)
    policies = {
        "all_observed": {
            "eligibility_rule": "all runs present at the selection snapshot",
            "minimum_wait_seconds": 0.0,
            **_score_selection(all_runs, selection_states, outcome_states, total),
        },
        "terminal_status": {
            "eligibility_rule": (
                "run status is completed, failed, or interrupted"
            ),
            "minimum_wait_seconds": None,
            **_score_selection(
                terminal_runs,
                selection_states,
                outcome_states,
                total,
            ),
        },
        "event_watermark": {
            "eligibility_rule": (
                "latest run event is older than the configured watermark"
            ),
            "minimum_wait_seconds": watermark_seconds,
            **_score_selection(
                watermark_runs,
                selection_states,
                outcome_states,
                total,
            ),
        },
        "observed_quiescence": {
            "eligibility_rule": (
                "private run fingerprint was unchanged from snapshot A to B"
            ),
            "minimum_wait_seconds": observed_quiescence_seconds,
            **_score_selection(
                quiescent_runs,
                selection_states,
                outcome_states,
                total,
            ),
        },
    }
    return {
        "selection_snapshot_run_count": total,
        "new_run_count_in_outcome_snapshot": len(
            set(outcome_states) - set(selection_states)
        ),
        "policies": policies,
    }


def _capture(database: Path) -> Tuple[Path, datetime, int]:
    snapshot, attempts = _consistent_snapshot(database)
    return snapshot, datetime.now(timezone.utc), attempts


def _cleanup(snapshot: Path) -> None:
    snapshot.unlink(missing_ok=True)
    Path(f"{snapshot}-wal").unlink(missing_ok=True)
    Path(f"{snapshot}-shm").unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--watermark-seconds", type=float, default=30.0)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.interval_seconds <= 0:
        parser.error("--interval-seconds must be positive")
    if arguments.watermark_seconds < 0:
        parser.error("--watermark-seconds cannot be negative")

    snapshots = []
    captures = []
    attempts = []
    states = []
    try:
        for index in range(3):
            snapshot, captured_at, attempt_count = _capture(arguments.database)
            snapshots.append(snapshot)
            captures.append(captured_at)
            attempts.append(attempt_count)
            states.append(_load_private_states(snapshot))
            if index < 2:
                time.sleep(arguments.interval_seconds)

        observed_ab = (captures[1] - captures[0]).total_seconds()
        observed_bc = (captures[2] - captures[1]).total_seconds()
        evaluation = _evaluate_policies(
            states[0],
            states[1],
            states[2],
            captures[1],
            arguments.watermark_seconds,
            observed_ab,
        )
        snapshot_manifest = {
            "snapshot_sha256": [sha256_path(snapshot) for snapshot in snapshots],
            "snapshot_bytes": [snapshot.stat().st_size for snapshot in snapshots],
            "backup_attempts": attempts,
            "integrity_checks": [
                next(iter(state.values()))["integrity_check"] if state else "ok"
                for state in states
            ],
        }
    finally:
        for snapshot in snapshots:
            _cleanup(snapshot)

    report = {
        "schema_version": "sri.experiment.dataset-cut-policy.v1",
        "experiment": {
            "name": "privacy-safe-live-dataset-cut-policy-pilot",
            "evidence_grade": "Experimental",
            "source_database_basename": arguments.database.name,
            "requested_interval_seconds": arguments.interval_seconds,
            "observed_intervals_seconds": [observed_ab, observed_bc],
            "watermark_seconds": arguments.watermark_seconds,
            "source_query_only_enforced": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "This is one three-snapshot observational time series.",
                "Policy assignment is deterministic, not randomized.",
                "Stable fingerprints do not prove that all source events arrived.",
                "The pilot cannot estimate long-window drift or causal policy effects.",
            ],
        },
        "snapshot_manifest": snapshot_manifest,
        "evaluation": evaluation,
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    integrity_passed = all(
        item.lower() == "ok"
        for item in snapshot_manifest["integrity_checks"]
    )
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "three-snapshot cut-policy pilot completed",
        "passed": (
            privacy_passed
            and integrity_passed
            and evaluation["selection_snapshot_run_count"] > 0
        ),
    }
    output = write_report(
        EXPERIMENT_DIR,
        "dataset-cut-policy",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "observed_intervals_seconds": (
                    report["experiment"]["observed_intervals_seconds"]
                ),
                "evaluation": evaluation,
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
