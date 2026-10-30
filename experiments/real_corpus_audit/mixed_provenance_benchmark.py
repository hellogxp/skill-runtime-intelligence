#!/usr/bin/env python3
"""Test transcript refresh against correlated official-hook evidence."""

import argparse
import json
import sys
import tempfile
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
from skill_runtime_intelligence.adapters.codex import CodexAdapter
from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.discovery import parse_skill
from skill_runtime_intelligence.storage import Storage


def _record(index: int, outer_type: str, payload: Dict[str, Any]):
    return {
        "timestamp": f"2026-07-30T02:00:{index:02d}Z",
        "type": outer_type,
        "payload": payload,
    }


def _write_transcript(
    path: Path,
    root: Path,
    skill_file: Path,
    *,
    completed: bool,
) -> None:
    records = [
        _record(
            0,
            "session_meta",
            {"id": "shared-source-session", "cwd": str(root)},
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
                "call_id": "transcript-call",
                "input": {"cmd": f"sed -n 1,80p {skill_file}"},
            },
        ),
    ]
    if completed:
        records.extend(
            [
                _record(
                    3,
                    "response_item",
                    {
                        "type": "function_call_output",
                        "call_id": "transcript-call",
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
    path.write_text(
        "".join(json.dumps(record) + "\n" for record in records),
        encoding="utf-8",
    )


def _hook_envelope(skill_file: Path) -> Dict[str, Any]:
    return {
        "event_id": "official-hook-event",
        "event_type": "skill.activated",
        "occurred_at": "2026-07-30T02:00:02Z",
        "session_id": "shared-source-session",
        "turn_id": "turn-1",
        "activation_mode": "explicit_tool",
        "skill": {
            "name": "pdf",
            "description": "Controlled PDF Skill",
            "source_path": str(skill_file),
        },
        "source": {
            "adapter": "codex",
            "adapter_version": "controlled",
            "collection_mode": "official_hook",
            "source_event_id": "official-hook-event",
            "record_locator": "hook:official-hook-event",
        },
        "evidence": {
            "grade": "observed",
            "confidence": 1.0,
            "basis": "Official runtime hook",
        },
        "payload": {"tool_name": "Skill"},
    }


def _metrics(storage: Storage) -> Dict[str, Any]:
    rows = storage.connection.execute(
        """
        SELECT collection_mode, session_id, correlation_key
        FROM sessions
        ORDER BY collection_mode, session_id
        """
    ).fetchall()
    session_ids = {str(row["session_id"]) for row in rows}
    modes = [str(row["collection_mode"]) for row in rows]
    correlation_keys = {str(row["correlation_key"]) for row in rows}
    hook_events = int(
        storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM normalized_events e
            JOIN sessions s ON s.session_id = e.session_id
            WHERE s.collection_mode = 'official_hook'
            """
        ).fetchone()[0]
    )
    hook_raw = int(
        storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM raw_source_records r
            JOIN sessions s ON s.session_id = r.session_id
            WHERE s.collection_mode = 'official_hook'
            """
        ).fetchone()[0]
    )
    hook_runs = int(
        storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM skill_runs sr
            JOIN sessions s ON s.session_id = sr.session_id
            WHERE s.collection_mode = 'official_hook'
            """
        ).fetchone()[0]
    )
    cross_source_relationships = int(
        storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM derived_relationships dr
            JOIN normalized_events parent
              ON parent.event_id = dr.source_event_id
            JOIN normalized_events child
              ON child.event_id = dr.target_event_id
            WHERE parent.session_id != child.session_id
            """
        ).fetchone()[0]
    )
    return {
        "session_count": len(rows),
        "distinct_session_count": len(session_ids),
        "official_hook_session_count": modes.count("official_hook"),
        "transcript_session_count": modes.count("transcript_fallback"),
        "correlation_key_count": len(correlation_keys),
        "official_hook_event_count": hook_events,
        "official_hook_raw_count": hook_raw,
        "official_hook_run_count": hook_runs,
        "cross_source_relationship_count": cross_source_relationships,
    }


def _trial(root: Path) -> Dict[str, Any]:
    root.mkdir(parents=True)
    skill_file = root / "skills" / "pdf" / "SKILL.md"
    skill_file.parent.mkdir(parents=True)
    skill_file.write_text(
        "---\nname: pdf\ndescription: Controlled PDF Skill\n---\nFixture.\n",
        encoding="utf-8",
    )
    skill = parse_skill(skill_file)
    transcript = root / "session.jsonl"
    database = root / "panorama.db"
    adapter = CodexAdapter(root)
    _write_transcript(
        transcript,
        root,
        skill_file,
        completed=False,
    )
    storage = Storage(database)
    try:
        storage.replace_skills([skill.to_dict()])
        session, raw, events, runs = adapter.parse(transcript, [skill])
        storage.replace_session(session, raw, events, runs)
        storage.append_collector_events(
            normalize_collector_payload(_hook_envelope(skill_file))
        )
        before = _metrics(storage)
        _write_transcript(
            transcript,
            root,
            skill_file,
            completed=True,
        )
        session, raw, events, runs = adapter.parse(transcript, [skill])
        storage.replace_session(session, raw, events, runs)
        after = _metrics(storage)
    finally:
        storage.close()
    return {
        "before": before,
        "after": after,
        "hook_evidence_preserved": all(
            after[name] == before[name] == 1
            for name in (
                "official_hook_event_count",
                "official_hook_raw_count",
                "official_hook_run_count",
                "official_hook_session_count",
            )
        ),
        "correlation_group_preserved": (
            after["session_count"] == 2
            and after["distinct_session_count"] == 2
            and after["correlation_key_count"] == 1
            and after["transcript_session_count"] == 1
        ),
        "cross_source_relationship_available": (
            after["cross_source_relationship_count"] > 0
        ),
    }


def run_experiment(trials: int) -> Dict[str, Any]:
    if trials < 1:
        raise ValueError("trials must be positive")
    results: List[Dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="sri-mixed-provenance-") as directory:
        root = Path(directory)
        for index in range(trials):
            results.append(_trial(root / f"trial-{index}"))
    metrics = {
        "trial_count": trials,
        "hook_evidence_preserved": sum(
            result["hook_evidence_preserved"] for result in results
        ),
        "correlation_group_preserved": sum(
            result["correlation_group_preserved"] for result in results
        ),
        "cross_source_relationship_available": sum(
            result["cross_source_relationship_available"]
            for result in results
        ),
    }
    preservation_passed = metrics["hook_evidence_preserved"] == trials
    correlation_passed = metrics["correlation_group_preserved"] == trials
    merge_passed = (
        metrics["cross_source_relationship_available"] == trials
    )
    report = {
        "schema_version": "sri.experiment.mixed-provenance-reconciliation.v1",
        "experiment": {
            "name": "mixed-transcript-official-hook-reconciliation",
            "evidence_grade": "Experimental",
            "production_adapters": True,
            "isolated_temporary_database": True,
            "synthetic_sources": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "limitations": [
                "Synthetic sources are not independent live Agent sessions.",
                "Deterministic trials do not estimate field failure rates.",
                "Absence of a cross-session edge does not specify the correct merge algorithm.",
            ],
        },
        "metrics": metrics,
        "gates": {
            "official_hook_evidence_preservation": {
                "passed": preservation_passed,
            },
            "correlation_group_preservation": {
                "passed": correlation_passed,
            },
            "merged_cross_source_relationship_plane": {
                "passed": merge_passed,
            },
        },
        "gate": {
            "name": "mixed-provenance preservation and merge",
            "passed": preservation_passed
            and correlation_passed
            and merge_passed,
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
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_experiment(arguments.trials)
    output = write_report(
        EXPERIMENT_DIR,
        "mixed-provenance",
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
