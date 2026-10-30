#!/usr/bin/env python3
"""Audit whether live multi-Adapter evidence supports cross-Agent claims."""

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _consistent_snapshot,
    _contains_forbidden_row_data,
    _snapshot_manifest,
)
from skill_runtime_intelligence.storage import Storage


DEFAULT_THRESHOLDS = {
    "minimum_adapter_count": 2,
    "descriptive_runs_per_adapter": 5,
    "confirmatory_runs_per_adapter": 20,
    "maximum_run_imbalance_ratio": 3.0,
    "minimum_shared_skill_digests": 2,
    "minimum_shared_event_stages": 3,
    "minimum_activation_runs_per_adapter": 2,
    "minimum_verified_outcome_runs_per_adapter": 2,
    "minimum_failed_event_runs_per_adapter": 2,
    "minimum_adjudicated_labels_per_adapter": 20,
}


def _records(storage: Storage) -> List[Dict[str, Any]]:
    records = []
    for run in storage.list_skill_runs(limit=100_000):
        detail = storage.get_skill_run(run["skill_run_id"])
        if not detail:
            continue
        events = [
            event
            for event in detail.get("events", [])
            if not event.get("context_only")
        ]
        records.append(
            {
                "adapter": str(run.get("adapter") or "unknown"),
                "session_key": run.get("session_id"),
                "skill_digest": run.get("digest"),
                "event_types": {
                    str(event.get("event_type") or "unknown")
                    for event in events
                },
                "event_stages": {
                    str(event.get("stage") or "unknown") for event in events
                },
                "explicit_failed_event": any(
                    event.get("status") == "failed" for event in events
                ),
            }
        )
    return records


def _criterion(name: str, passed: bool, detail: str) -> Dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def _aggregate(
    records: Iterable[Dict[str, Any]],
    thresholds: Dict[str, Any] = None,
) -> tuple:
    thresholds = dict(DEFAULT_THRESHOLDS if thresholds is None else thresholds)
    by_adapter: Dict[str, Dict[str, Any]] = {}
    digest_adapters = defaultdict(set)

    for record in records:
        adapter = str(record.get("adapter") or "unknown")
        if adapter not in by_adapter:
            by_adapter[adapter] = {
                "run_count": 0,
                "session_keys": set(),
                "skill_digests": set(),
                "event_types": set(),
                "event_stages": set(),
                "observed_activation_runs": 0,
                "verified_outcome_runs": 0,
                "explicit_failed_event_runs": 0,
            }
        aggregate = by_adapter[adapter]
        aggregate["run_count"] += 1
        aggregate["session_keys"].add(record.get("session_key"))
        digest = record.get("skill_digest")
        if digest:
            aggregate["skill_digests"].add(digest)
            digest_adapters[digest].add(adapter)
        event_types = set(record.get("event_types") or [])
        aggregate["event_types"].update(event_types)
        aggregate["event_stages"].update(record.get("event_stages") or [])
        aggregate["observed_activation_runs"] += (
            "skill.activated" in event_types
        )
        aggregate["verified_outcome_runs"] += (
            "outcome.verified" in event_types
        )
        aggregate["explicit_failed_event_runs"] += bool(
            record.get("explicit_failed_event")
        )

    adapter_rows = []
    stage_sets = []
    run_counts = []
    for adapter in sorted(by_adapter):
        aggregate = by_adapter[adapter]
        run_counts.append(aggregate["run_count"])
        stage_sets.append(set(aggregate["event_stages"]))
        adapter_rows.append(
            {
                "adapter": adapter,
                "run_count": aggregate["run_count"],
                "session_count": len(aggregate["session_keys"]),
                "skill_digest_count": len(aggregate["skill_digests"]),
                "event_type_count": len(aggregate["event_types"]),
                "event_stage_count": len(aggregate["event_stages"]),
                "observed_activation_runs": aggregate[
                    "observed_activation_runs"
                ],
                "verified_outcome_runs": aggregate[
                    "verified_outcome_runs"
                ],
                "explicit_failed_event_runs": aggregate[
                    "explicit_failed_event_runs"
                ],
                "adjudicated_label_count": 0,
            }
        )

    shared_stages = (
        sorted(set.intersection(*stage_sets)) if stage_sets else []
    )
    shared_skill_digest_count = sum(
        len(adapters) >= thresholds["minimum_adapter_count"]
        for adapters in digest_adapters.values()
    )
    descriptive_adapters = [
        row
        for row in adapter_rows
        if row["run_count"] >= thresholds["descriptive_runs_per_adapter"]
    ]
    confirmatory_adapters = [
        row
        for row in adapter_rows
        if row["run_count"] >= thresholds["confirmatory_runs_per_adapter"]
    ]
    imbalance_ratio = (
        max(run_counts) / min(run_counts) if run_counts else None
    )
    minimum_adapter_count = thresholds["minimum_adapter_count"]

    presence_checks = [
        _criterion(
            "minimum_adapter_count",
            len(adapter_rows) >= minimum_adapter_count,
            f"{len(adapter_rows)}/{minimum_adapter_count} adapters",
        ),
        _criterion(
            "each_present_adapter_has_a_run",
            bool(adapter_rows)
            and all(row["run_count"] >= 1 for row in adapter_rows),
            "support presence only; no balance or quality implication",
        ),
    ]
    descriptive_checks = [
        _criterion(
            "minimum_adapters_with_descriptive_runs",
            len(descriptive_adapters) >= minimum_adapter_count,
            (
                f"{len(descriptive_adapters)}/{minimum_adapter_count} adapters "
                f"have >= {thresholds['descriptive_runs_per_adapter']} runs"
            ),
        ),
        _criterion(
            "shared_skill_digest_available",
            shared_skill_digest_count >= 1,
            f"{shared_skill_digest_count} shared digest groups",
        ),
        _criterion(
            "minimum_shared_event_stages",
            len(shared_stages) >= thresholds["minimum_shared_event_stages"],
            (
                f"{len(shared_stages)}/"
                f"{thresholds['minimum_shared_event_stages']} shared stages"
            ),
        ),
    ]

    has_confirmatory_adapters = (
        len(confirmatory_adapters) >= minimum_adapter_count
    )

    def all_confirmatory_at_least(field: str, threshold: int) -> bool:
        return has_confirmatory_adapters and all(
            row[field] >= threshold for row in confirmatory_adapters
        )

    confirmatory_checks = [
        _criterion(
            "minimum_adapters_with_confirmatory_runs",
            has_confirmatory_adapters,
            (
                f"{len(confirmatory_adapters)}/{minimum_adapter_count} adapters "
                f"have >= {thresholds['confirmatory_runs_per_adapter']} runs"
            ),
        ),
        _criterion(
            "run_count_balance",
            bool(run_counts)
            and imbalance_ratio
            <= thresholds["maximum_run_imbalance_ratio"],
            (
                f"max/min={imbalance_ratio:.3f}; limit="
                f"{thresholds['maximum_run_imbalance_ratio']}"
                if imbalance_ratio is not None
                else "no runs"
            ),
        ),
        _criterion(
            "minimum_shared_skill_digests",
            shared_skill_digest_count
            >= thresholds["minimum_shared_skill_digests"],
            (
                f"{shared_skill_digest_count}/"
                f"{thresholds['minimum_shared_skill_digests']} shared groups"
            ),
        ),
        _criterion(
            "activation_coverage_per_adapter",
            all_confirmatory_at_least(
                "observed_activation_runs",
                thresholds["minimum_activation_runs_per_adapter"],
            ),
            "requires observed activation evidence in every eligible adapter",
        ),
        _criterion(
            "verified_outcome_coverage_per_adapter",
            all_confirmatory_at_least(
                "verified_outcome_runs",
                thresholds["minimum_verified_outcome_runs_per_adapter"],
            ),
            "requires verified outcomes in every eligible adapter",
        ),
        _criterion(
            "failed_event_coverage_per_adapter",
            all_confirmatory_at_least(
                "explicit_failed_event_runs",
                thresholds["minimum_failed_event_runs_per_adapter"],
            ),
            "requires explicit failures in every eligible adapter",
        ),
        _criterion(
            "task_alignment_key_available",
            False,
            "current SkillRun schema has no privacy-safe paired-task key",
        ),
        _criterion(
            "adjudicated_labels_per_adapter",
            False,
            (
                "current runtime audit has 0 independently adjudicated labels; "
                "requires "
                f"{thresholds['minimum_adjudicated_labels_per_adapter']} per adapter"
            ),
        ),
    ]

    metrics = {
        "run_count": sum(run_counts),
        "adapter_count": len(adapter_rows),
        "adapter_coverage": adapter_rows,
        "adapters_with_descriptive_run_count": len(descriptive_adapters),
        "adapters_with_confirmatory_run_count": len(confirmatory_adapters),
        "run_count_imbalance_ratio": imbalance_ratio,
        "shared_skill_digest_count": shared_skill_digest_count,
        "shared_event_stages": shared_stages,
        "task_alignment_key_available": False,
    }
    readiness = {
        "thresholds": thresholds,
        "presence": {
            "checks": presence_checks,
            "passed_count": sum(row["passed"] for row in presence_checks),
            "criterion_count": len(presence_checks),
            "multi_adapter_presence": all(
                row["passed"] for row in presence_checks
            ),
        },
        "descriptive": {
            "checks": descriptive_checks,
            "passed_count": sum(row["passed"] for row in descriptive_checks),
            "criterion_count": len(descriptive_checks),
            "cross_agent_descriptive_ready": all(
                row["passed"] for row in descriptive_checks
            ),
        },
        "confirmatory": {
            "checks": confirmatory_checks,
            "passed_count": sum(row["passed"] for row in confirmatory_checks),
            "criterion_count": len(confirmatory_checks),
            "cross_agent_confirmatory_ready": all(
                row["passed"] for row in confirmatory_checks
            ),
        },
    }
    return metrics, readiness


def run_audit(database: Path) -> Dict[str, Any]:
    snapshot, snapshot_attempts = _consistent_snapshot(database)
    try:
        storage = Storage(snapshot)
        try:
            metrics, readiness = _aggregate(_records(storage))
        finally:
            storage.close()
        dataset_manifest = _snapshot_manifest(snapshot, metrics, readiness)
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)

    report = {
        "schema_version": "sri.experiment.cross-agent-coverage-readiness.v2",
        "experiment": {
            "name": "privacy-safe-cross-agent-coverage-readiness-audit",
            "evidence_grade": "Derived",
            "source_database_basename": database.name,
            "consistent_snapshot": True,
            "snapshot_backup_attempts": snapshot_attempts,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Thresholds are exploratory and were not preregistered.",
                "Adapter counts do not establish task alignment or outcome equivalence.",
                "The database contains one local user's runs.",
                "Independently adjudicated labels are not represented by the current runtime audit.",
                "Model adjudication must preserve model, prompt, sampling, and disagreement provenance and is not human evidence.",
                "Passing presence or descriptive gates does not authorize causal claims.",
            ],
        },
        "metrics": metrics,
        "readiness": readiness,
        "dataset_manifest": dataset_manifest,
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "privacy-safe cross-Agent coverage audit completed",
        "passed": (
            privacy_passed
            and metrics["run_count"] > 0
            and dataset_manifest["integrity_check"].lower() == "ok"
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_audit(arguments.database)
    output = write_report(
        EXPERIMENT_DIR,
        "cross-agent-coverage-readiness",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "readiness": report["readiness"],
                "gate": report["gate"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
