#!/usr/bin/env python3
"""Measure terminality and evidence-sufficiency transitions in one cohort."""

import argparse
import json
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import sha256_path, write_report
from experiments.real_corpus_audit.run_benchmark import (
    _consistent_snapshot,
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.storage import Storage


TERMINAL_STATUSES = {"completed", "failed", "interrupted"}


def _state(run: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
    owned_events = [
        event
        for event in detail.get("events", [])
        if not event.get("context_only")
    ]
    event_types = {
        str(event.get("event_type") or "unknown") for event in owned_events
    }
    explicit_failure = any(
        str(event.get("status") or "") == "failed"
        for event in owned_events
    )
    observed_activation = "skill.activated" in event_types
    verified_outcome = "outcome.verified" in event_types
    evidence_sufficient = observed_activation and (
        verified_outcome or explicit_failure
    )
    terminal = str(run.get("status") or "unknown") in TERMINAL_STATUSES
    return {
        "terminal": terminal,
        "observed_activation": observed_activation,
        "verified_outcome": verified_outcome,
        "explicit_failure": explicit_failure,
        "evidence_sufficient": evidence_sufficient,
        "state": (
            f"{'terminal' if terminal else 'nonterminal'}__"
            f"{'sufficient' if evidence_sufficient else 'insufficient'}"
        ),
    }


def _load_private_states(snapshot: Path) -> Tuple[Dict[str, Dict[str, Any]], str]:
    """Use private run keys for matching; callers only emit aggregates."""
    storage = Storage(snapshot)
    try:
        states = {}
        for run in storage.list_skill_runs(limit=100_000):
            detail = storage.get_skill_run(run["skill_run_id"])
            if detail:
                states[run["skill_run_id"]] = _state(run, detail)
        integrity = str(storage.connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0])
    finally:
        storage.close()
    return states, integrity


def _counts(states: Dict[str, Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(state["state"] for state in states.values())
    return {key: counts[key] for key in sorted(counts)}


def _evaluate(
    before: Dict[str, Dict[str, Any]],
    after: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    cohort = set(before)
    retained = cohort & set(after)
    missing = cohort - set(after)
    transitions = Counter(
        (before[run_id]["state"], after[run_id]["state"])
        for run_id in retained
    )
    changed = sum(
        count for (source, target), count in transitions.items()
        if source != target
    )
    return {
        "cohort_run_count": len(cohort),
        "retained_run_count": len(retained),
        "missing_run_count": len(missing),
        "new_run_count": len(set(after) - cohort),
        "before_state_counts": _counts(before),
        "after_state_counts_for_cohort": _counts(
            {run_id: after[run_id] for run_id in retained}
        ),
        "transition_counts": [
            {
                "from_state": source,
                "to_state": target,
                "run_count": count,
            }
            for (source, target), count in sorted(transitions.items())
        ],
        "changed_state_count": changed,
        "changed_state_fraction": (
            changed / len(retained) if retained else None
        ),
    }


def _cleanup(snapshot: Path) -> None:
    snapshot.unlink(missing_ok=True)
    Path(f"{snapshot}-wal").unlink(missing_ok=True)
    Path(f"{snapshot}-shm").unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.interval_seconds <= 0:
        parser.error("--interval-seconds must be positive")

    snapshots = []
    captures = []
    attempts = []
    states = []
    integrity_checks = []
    try:
        for index in range(2):
            snapshot, attempt_count = _consistent_snapshot(arguments.database)
            snapshots.append(snapshot)
            captures.append(datetime.now(timezone.utc))
            attempts.append(attempt_count)
            private_states, integrity = _load_private_states(snapshot)
            states.append(private_states)
            integrity_checks.append(integrity)
            if index == 0:
                time.sleep(arguments.interval_seconds)

        evaluation = _evaluate(states[0], states[1])
        observed_interval = (captures[1] - captures[0]).total_seconds()
        snapshot_manifest = {
            "snapshot_sha256": [sha256_path(item) for item in snapshots],
            "snapshot_bytes": [item.stat().st_size for item in snapshots],
            "backup_attempts": attempts,
            "integrity_checks": integrity_checks,
        }
    finally:
        for snapshot in snapshots:
            _cleanup(snapshot)

    report = {
        "schema_version": "sri.experiment.cohort-evidence-transition.v1",
        "experiment": {
            "name": "privacy-safe-cohort-evidence-transition-pilot",
            "evidence_grade": "Experimental",
            "source_database_basename": arguments.database.name,
            "requested_interval_seconds": arguments.interval_seconds,
            "observed_interval_seconds": observed_interval,
            "cohort_rule": "all runs present in snapshot A",
            "evidence_sufficiency_rule": (
                "observed skill activation and either verified outcome or "
                "explicit failed event"
            ),
            "source_query_only_enforced": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "This is one short observational interval on one local database.",
                "No intervention was assigned and no causal effect is estimated.",
                "Missing evidence may reflect adapter capability rather than run quality.",
                "Private run keys are used only for local matching and are not emitted.",
            ],
        },
        "snapshot_manifest": snapshot_manifest,
        "evaluation": evaluation,
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    integrity_passed = all(
        item.lower() == "ok" for item in integrity_checks
    )
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "cohort evidence-transition pilot completed",
        "passed": (
            privacy_passed
            and integrity_passed
            and evaluation["cohort_run_count"] > 0
        ),
    }
    output = write_report(
        EXPERIMENT_DIR,
        "cohort-evidence-transition",
        report,
        arguments.output,
    )
    print(json.dumps({
        "observed_interval_seconds": observed_interval,
        "evaluation": evaluation,
        "privacy_audit": report["privacy_audit"],
        "gate": report["gate"],
    }, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
