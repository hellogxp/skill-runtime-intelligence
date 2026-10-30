#!/usr/bin/env python3
"""Controlled mechanism experiment for collection epochs and late arrivals."""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.indexer import (
    _index_changed_batch,
    _source_watermark,
)
from skill_runtime_intelligence.storage import Storage


class _ControlledAdapter:
    def __init__(
        self,
        database: Path,
        *,
        mutate_source: Path = None,
        create_source: Path = None,
        fail: bool = False,
    ):
        self.database = database
        self.mutate_source = mutate_source
        self.create_source = create_source
        self.fail = fail
        self.statuses_seen: List[str] = []

    def parse(self, source_path: Path, skills: List[Any]):
        storage = Storage(self.database)
        try:
            self.statuses_seen.append(
                str(storage.collection_epoch("codex").get("status"))
            )
        finally:
            storage.close()
        if self.mutate_source is not None:
            previous = self.mutate_source.stat().st_mtime_ns
            self.mutate_source.write_text(
                self.mutate_source.read_text(encoding="utf-8") + "{}\n",
                encoding="utf-8",
            )
            changed = max(time.time_ns(), previous + 1)
            os.utime(self.mutate_source, ns=(changed, changed))
        if self.create_source is not None:
            self.create_source.write_text("{}\n", encoding="utf-8")
        if self.fail:
            raise RuntimeError("controlled adapter failure")
        return (
            {
                "session_id": "controlled-session",
                "adapter": "codex",
                "adapter_version": "controlled",
                "source_path": str(source_path),
                "source_format_version": "controlled",
                "title": "",
                "cwd": "",
                "model": "",
                "agent_version": "",
                "started_at": None,
                "ended_at": None,
                "duration_ms": None,
                "status": "incomplete",
                "completeness": "partial",
                "event_count": 0,
            },
            [],
            [],
            [],
        )


def _trial(root: Path, *, inject_late_arrival: bool) -> Dict[str, Any]:
    root.mkdir(parents=True)
    primary = root / "primary.jsonl"
    boundary = root / "boundary.jsonl"
    primary.write_text("{}\n", encoding="utf-8")
    boundary.write_text("{}\n", encoding="utf-8")
    database = root / "panorama.db"
    before = {
        primary: primary.stat().st_mtime_ns,
        boundary: boundary.stat().st_mtime_ns,
    }
    adapter = _ControlledAdapter(
        database,
        mutate_source=boundary if inject_late_arrival else None,
    )
    completed = _index_changed_batch(
        database,
        adapter,
        [],
        [primary],
        before,
    )
    after = {
        primary: primary.stat().st_mtime_ns,
        boundary: boundary.stat().st_mtime_ns,
    }
    return {
        "running_seen": adapter.statuses_seen == ["running"],
        "completed": completed.get("status") == "completed",
        "late_arrival_count": completed.get("late_arrival_count"),
        "watermark_changed": (
            _source_watermark(before) != _source_watermark(after)
        ),
    }


def _failure_trial(root: Path) -> Dict[str, Any]:
    root.mkdir(parents=True)
    source = root / "failure.jsonl"
    source.write_text("{}\n", encoding="utf-8")
    database = root / "panorama.db"
    boundary = {source: source.stat().st_mtime_ns}
    adapter = _ControlledAdapter(database, fail=True)
    raised = False
    try:
        _index_changed_batch(database, adapter, [], [source], boundary)
    except RuntimeError as error:
        raised = str(error) == "controlled adapter failure"
    storage = Storage(database)
    try:
        epoch = storage.collection_epoch("codex")
    finally:
        storage.close()
    return {
        "running_seen": adapter.statuses_seen == ["running"],
        "failure_propagated": raised,
        "failed": epoch.get("status") == "failed",
        "failed_source_count": epoch.get("failed_source_count"),
    }


def _new_source_trial(root: Path) -> Dict[str, Any]:
    root.mkdir(parents=True)
    primary = root / "primary.jsonl"
    primary.write_text("{}\n", encoding="utf-8")
    database = root / "panorama.db"
    before = {primary: primary.stat().st_mtime_ns}
    adapter = _ControlledAdapter(
        database,
        create_source=root / "late-created.jsonl",
    )
    completed = _index_changed_batch(
        database,
        adapter,
        [],
        [primary],
        before,
        source_boundary_probe=lambda: {
            source: source.stat().st_mtime_ns
            for source in root.glob("*.jsonl")
        },
    )
    return {
        "running_seen": adapter.statuses_seen == ["running"],
        "completed": completed.get("status") == "completed",
        "late_arrival_count": completed.get("late_arrival_count"),
    }


def run_experiment(paired_trials: int, failure_trials: int) -> Dict[str, Any]:
    if paired_trials < 1 or failure_trials < 1:
        raise ValueError("trial counts must be positive")
    injected = []
    controls = []
    new_sources = []
    failures = []
    with tempfile.TemporaryDirectory(prefix="sri-epoch-mechanism-") as directory:
        root = Path(directory)
        for index in range(paired_trials):
            injected.append(
                _trial(root / f"injected-{index}", inject_late_arrival=True)
            )
            controls.append(
                _trial(root / f"control-{index}", inject_late_arrival=False)
            )
            new_sources.append(_new_source_trial(root / f"new-{index}"))
        for index in range(failure_trials):
            failures.append(_failure_trial(root / f"failure-{index}"))

    metrics = {
        "paired_trial_count": paired_trials,
        "injected_late_arrivals": paired_trials,
        "detected_late_arrivals": sum(
            trial["late_arrival_count"] == 1 for trial in injected
        ),
        "missed_late_arrivals": sum(
            trial["late_arrival_count"] != 1 for trial in injected
        ),
        "control_false_positives": sum(
            trial["late_arrival_count"] != 0 for trial in controls
        ),
        "created_source_trials": paired_trials,
        "detected_created_sources": sum(
            trial["late_arrival_count"] == 1 for trial in new_sources
        ),
        "running_state_observed": sum(
            trial["running_seen"] for trial in injected + controls
        ),
        "completed_state_observed": sum(
            trial["completed"] for trial in injected + controls
        ),
        "watermark_change_detected": sum(
            trial["watermark_changed"] for trial in injected
        ),
        "control_watermark_changes": sum(
            trial["watermark_changed"] for trial in controls
        ),
        "failure_trial_count": failure_trials,
        "failed_state_observed": sum(
            trial["failed"] for trial in failures
        ),
        "failure_propagated": sum(
            trial["failure_propagated"] for trial in failures
        ),
        "failed_source_count_exact": sum(
            trial["failed_source_count"] == 1 for trial in failures
        ),
    }
    expected_completed = paired_trials * 2
    passed = (
        metrics["detected_late_arrivals"] == paired_trials
        and metrics["missed_late_arrivals"] == 0
        and metrics["control_false_positives"] == 0
        and metrics["detected_created_sources"] == paired_trials
        and metrics["running_state_observed"] == expected_completed
        and metrics["completed_state_observed"] == expected_completed
        and metrics["watermark_change_detected"] == paired_trials
        and metrics["control_watermark_changes"] == 0
        and metrics["failed_state_observed"] == failure_trials
        and metrics["failure_propagated"] == failure_trials
        and metrics["failed_source_count_exact"] == failure_trials
    )
    report = {
        "schema_version": "sri.experiment.collection-epoch-mechanism.v1",
        "experiment": {
            "name": "controlled-collection-epoch-mechanism",
            "evidence_grade": "Experimental",
            "isolated_temporary_database": True,
            "synthetic_adapter": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Trials validate local mechanism behavior, not live watcher deployment.",
                "Deterministic repetitions are not independent workload samples.",
                "Injected file changes do not estimate natural late-arrival frequency.",
                "The result does not prove upstream source completeness.",
            ],
        },
        "metrics": metrics,
        "gate": {
            "name": "collection epoch transitions and late-arrival accounting",
            "passed": passed,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"]["passed"] = passed and privacy_passed
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paired-trials", type=int, default=8)
    parser.add_argument("--failure-trials", type=int, default=4)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment(
        arguments.paired_trials,
        arguments.failure_trials,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "collection-epoch-mechanism",
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
