#!/usr/bin/env python3
"""Exercise collection epochs through the production Codex watch loop."""

import argparse
import json
import multiprocessing
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from experiments.real_corpus_audit.run_benchmark import (
    _contains_forbidden_row_data,
)
from skill_runtime_intelligence.indexer import watch_local
from skill_runtime_intelligence.storage import Storage


def _watch_worker(
    database: Path,
    sessions: Path,
    skills: Path,
) -> None:
    watch_local(
        database,
        sessions,
        [skills],
        interval_seconds=0.5,
    )


def _snapshot(database: Path) -> Dict[str, Any]:
    if not database.is_file():
        return {}
    storage = Storage(database)
    try:
        counts = storage.counts()
        sessions = storage.list_runs()
        epoch = storage.collection_epoch("codex")
    finally:
        storage.close()
    return {
        "session_count": counts["sessions"],
        "skill_count": counts["skills"],
        "skill_run_count": counts["skill_runs"],
        "event_count": counts["normalized_events"],
        "session_completed": (
            len(sessions) == 1 and sessions[0].get("status") == "completed"
        ),
        "epoch": int(epoch.get("epoch", 0) or 0),
        "epoch_status": epoch.get("status"),
        "epoch_source_count": epoch.get("source_count"),
        "epoch_removed_source_count": epoch.get("removed_source_count"),
    }


def _wait_for(database: Path, predicate, timeout: float = 8.0):
    deadline = time.monotonic() + timeout
    latest = {}
    while time.monotonic() < deadline:
        try:
            latest = _snapshot(database)
        except Exception:
            latest = {}
        if predicate(latest):
            return latest
        time.sleep(0.05)
    return latest


def _record(index: int, outer_type: str, payload: Dict[str, Any]):
    return {
        "timestamp": f"2026-07-30T01:00:{index:02d}Z",
        "type": outer_type,
        "payload": payload,
    }


def _write_records(path: Path, records) -> None:
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _trial(root: Path) -> Dict[str, Any]:
    sessions = root / "sessions"
    skills = root / "skills"
    sessions.mkdir(parents=True)
    skill_file = skills / "pdf" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\nname: pdf\ndescription: Controlled PDF Skill\n---\nFixture.\n",
        encoding="utf-8",
    )
    database = root / "panorama.db"
    context = multiprocessing.get_context("spawn")
    process = context.Process(
        target=_watch_worker,
        args=(database, sessions, skills),
    )
    process.start()
    cleaned = False
    try:
        ready = _wait_for(
            database,
            lambda state: state.get("skill_count") == 1,
        )
        session_file = sessions / "controlled.jsonl"
        records = [
            _record(
                0,
                "session_meta",
                {"id": "controlled-session", "cwd": str(root)},
            ),
            _record(
                1,
                "event_msg",
                {"type": "task_started", "turn_id": "turn-1"},
            ),
            _record(
                2,
                "response_item",
                {
                    "type": "function_call",
                    "name": "exec_command",
                    "call_id": "call-1",
                    "input": {"cmd": f"sed -n 1,80p {skill_file}"},
                },
            ),
        ]
        _write_records(session_file, records)
        initial = _wait_for(
            database,
            lambda state: (
                state.get("session_count") == 1
                and state.get("skill_run_count") == 1
                and state.get("epoch_status") == "completed"
            ),
        )
        first_epoch = int(initial.get("epoch", 0) or 0)
        records.extend(
            [
                _record(
                    3,
                    "response_item",
                    {
                        "type": "function_call_output",
                        "call_id": "call-1",
                        "output": "ok",
                    },
                ),
                _record(
                    4,
                    "event_msg",
                    {"type": "task_complete", "turn_id": "turn-1"},
                ),
            ]
        )
        _write_records(session_file, records)
        appended = _wait_for(
            database,
            lambda state: (
                state.get("epoch", 0) > first_epoch
                and state.get("session_completed")
                and state.get("epoch_status") == "completed"
            ),
        )
        second_epoch = int(appended.get("epoch", 0) or 0)
        session_file.unlink()
        time.sleep(1.25)
        deleted = _snapshot(database)
    finally:
        process.terminate()
        process.join(timeout=3)
        if process.is_alive():
            process.kill()
            process.join(timeout=3)
        cleaned = not process.is_alive()
    return {
        "watcher_ready": ready.get("skill_count") == 1,
        "initial_ingestion": (
            initial.get("session_count") == 1
            and initial.get("skill_run_count") == 1
            and first_epoch >= 1
        ),
        "append_reindexed": (
            second_epoch > first_epoch
            and appended.get("session_completed")
        ),
        "deletion_epoch_advanced": deleted.get("epoch", 0) > second_epoch,
        "deletion_count_recorded": (
            deleted.get("epoch_removed_source_count") == 1
        ),
        "session_retained_after_source_deletion": (
            deleted.get("session_count") == 1
        ),
        "watcher_process_cleaned": cleaned,
    }


def run_experiment(trials: int) -> Dict[str, Any]:
    if trials < 1:
        raise ValueError("trials must be positive")
    results = []
    with tempfile.TemporaryDirectory(prefix="sri-codex-watch-") as directory:
        root = Path(directory)
        for index in range(trials):
            results.append(_trial(root / f"trial-{index}"))
    metrics = {
        "trial_count": trials,
        "watcher_ready": sum(result["watcher_ready"] for result in results),
        "initial_ingestion": sum(
            result["initial_ingestion"] for result in results
        ),
        "append_reindexed": sum(
            result["append_reindexed"] for result in results
        ),
        "deletion_epoch_advanced": sum(
            result["deletion_epoch_advanced"] for result in results
        ),
        "deletion_count_recorded": sum(
            result["deletion_count_recorded"] for result in results
        ),
        "session_retained_after_source_deletion": sum(
            result["session_retained_after_source_deletion"]
            for result in results
        ),
        "watcher_process_cleaned": sum(
            result["watcher_process_cleaned"] for result in results
        ),
    }
    primary_passed = all(
        metrics[name] == trials
        for name in (
            "watcher_ready",
            "initial_ingestion",
            "append_reindexed",
            "watcher_process_cleaned",
        )
    )
    deletion_passed = (
        metrics["deletion_epoch_advanced"] == trials
        and metrics["deletion_count_recorded"] == trials
        and metrics["session_retained_after_source_deletion"] == trials
    )
    report = {
        "schema_version": "sri.experiment.codex-watch-epoch.v1",
        "experiment": {
            "name": "isolated-production-codex-watch-epoch",
            "evidence_grade": "Experimental",
            "production_adapter": True,
            "isolated_temporary_database": True,
            "synthetic_transcript": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Synthetic transcripts are not independent live Agent runs.",
                "Process termination tests harness cleanup, not graceful product shutdown.",
                "Three deterministic trials do not estimate field failure rates.",
            ],
        },
        "metrics": metrics,
        "gates": {
            "new_and_appended_source_watch_path": {
                "passed": primary_passed,
            },
            "deleted_source_collection_boundary": {
                "passed": deletion_passed,
            },
        },
        "gate": {
            "name": "production Codex watch epoch boundary",
            "passed": primary_passed and deletion_passed,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"]["passed"] = report["gate"]["passed"] and privacy_passed
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment(arguments.trials)
    output = write_report(
        EXPERIMENT_DIR,
        "codex-watch-epoch",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "gates": report["gates"],
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
