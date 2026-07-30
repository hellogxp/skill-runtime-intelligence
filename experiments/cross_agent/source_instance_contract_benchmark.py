#!/usr/bin/env python3
"""Exercise Agent-scoped official-hook source identity under label collisions."""

import argparse
import json
import sys
import tempfile
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
from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.hook_adapter import (
    CLAUDE_HOOK_ADAPTER_VERSION,
    OPENCODE_PLUGIN_ADAPTER_VERSION,
    QODER_HOOK_ADAPTER_VERSION,
    build_hook_envelopes,
)
from skill_runtime_intelligence.storage import Storage


AGENTS = ("qoder", "opencode", "claude-code")
ADAPTER_VERSIONS = {
    "qoder": QODER_HOOK_ADAPTER_VERSION,
    "opencode": OPENCODE_PLUGIN_ADAPTER_VERSION,
    "claude-code": CLAUDE_HOOK_ADAPTER_VERSION,
}


def _payload(event: str) -> Dict[str, Any]:
    payload = {
        "session_id": "deliberately-shared-session-label",
        "turn_id": "deliberately-shared-turn-label",
        "tool_name": "Bash",
        "tool_use_id": "deliberately-shared-call-label",
        "cwd": "/tmp/source-instance-contract",
    }
    if event == "PreToolUse":
        payload["tool_input"] = {"cmd": "true"}
    if event == "PostToolUse":
        payload["tool_response"] = {"success": True}
    return payload


def _trial(root: Path) -> Dict[str, Any]:
    database = root / "panorama.db"
    storage = Storage(database)
    try:
        for agent in AGENTS:
            for event in ("PreToolUse", "PostToolUse"):
                envelopes = build_hook_envelopes(
                    agent,
                    event,
                    _payload(event),
                )
                storage.append_collector_events(
                    normalize_collector_payload(envelopes)
                )

        before_append = storage.connection.execute(
            """
            SELECT COUNT(*) AS session_count,
                   COUNT(DISTINCT adapter) AS adapter_count,
                   COUNT(DISTINCT session_id) AS internal_session_count,
                   COUNT(DISTINCT correlation_key) AS correlation_group_count
            FROM sessions
            """
        ).fetchone()
        per_agent = storage.connection.execute(
            """
            SELECT adapter, COUNT(*) AS session_count,
                   SUM(event_count) AS event_count
            FROM sessions
            GROUP BY adapter
            """
        ).fetchall()
        event_identity = storage.connection.execute(
            """
            SELECT COUNT(*) AS event_count,
                   COUNT(DISTINCT event_id) AS distinct_event_count
            FROM normalized_events
            """
        ).fetchone()
        cross_source_relationships = storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM derived_relationships dr
            JOIN normalized_events source
              ON source.event_id = dr.source_event_id
            JOIN normalized_events target
              ON target.event_id = dr.target_event_id
            WHERE source.session_id != target.session_id
            """
        ).fetchone()[0]
        repeated_turn_labels = storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT turn_id, event_type
                FROM normalized_events
                WHERE turn_id IS NOT NULL
                GROUP BY turn_id, event_type
                HAVING COUNT(DISTINCT session_id) > 1
            )
            """
        ).fetchone()[0]

        append_envelopes = build_hook_envelopes(
            "qoder",
            "Stop",
            _payload("Stop"),
        )
        storage.append_collector_events(
            normalize_collector_payload(append_envelopes)
        )
        after_append_session_count = storage.connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]
        qoder_event_count = storage.connection.execute(
            """
            SELECT COUNT(*)
            FROM normalized_events e
            JOIN sessions s USING(session_id)
            WHERE s.adapter = 'qoder'
            """
        ).fetchone()[0]
    finally:
        storage.close()

    agent_rows = {
        str(row["adapter"]): {
            "sessions": int(row["session_count"]),
            "events": int(row["event_count"]),
        }
        for row in per_agent
    }
    return {
        "agent_count": int(before_append["adapter_count"]),
        "session_count_before_append": int(
            before_append["session_count"]
        ),
        "internal_session_count": int(
            before_append["internal_session_count"]
        ),
        "correlation_group_count": int(
            before_append["correlation_group_count"]
        ),
        "agents_with_one_session": sum(
            row["sessions"] == 1 for row in agent_rows.values()
        ),
        "agents_with_two_initial_events": sum(
            row["events"] == 2 for row in agent_rows.values()
        ),
        "event_count": int(event_identity["event_count"]),
        "distinct_event_count": int(
            event_identity["distinct_event_count"]
        ),
        "cross_source_relationship_count": int(
            cross_source_relationships
        ),
        "repeated_turn_event_label_groups": int(repeated_turn_labels),
        "session_count_after_same_agent_append": int(
            after_append_session_count
        ),
        "qoder_event_count_after_append": int(qoder_event_count),
    }


def run_experiment(trials: int) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-cross-agent-source-contract-"
    ) as directory:
        root = Path(directory)
        results = [
            _trial(root / f"trial-{trial}")
            for trial in range(1, trials + 1)
        ]

    exact_trials = sum(
        result["agent_count"] == len(AGENTS)
        and result["session_count_before_append"] == len(AGENTS)
        and result["internal_session_count"] == len(AGENTS)
        and result["correlation_group_count"] == len(AGENTS)
        and result["agents_with_one_session"] == len(AGENTS)
        and result["agents_with_two_initial_events"] == len(AGENTS)
        and result["event_count"] == len(AGENTS) * 2
        and result["distinct_event_count"] == len(AGENTS) * 2
        and result["cross_source_relationship_count"] == 0
        and result["repeated_turn_event_label_groups"] == 2
        and result["session_count_after_same_agent_append"] == len(AGENTS)
        and result["qoder_event_count_after_append"] == 3
        for result in results
    )
    metrics = {
        "trials": trials,
        "exact_contract_trials": exact_trials,
        "agent_profiles_per_trial": len(AGENTS),
        "same_agent_append_without_new_session_trials": sum(
            result["session_count_after_same_agent_append"] == len(AGENTS)
            for result in results
        ),
        "cross_agent_event_identity_collision_trials": sum(
            result["event_count"] != result["distinct_event_count"]
            for result in results
        ),
        "cross_source_relationship_trials": sum(
            result["cross_source_relationship_count"] > 0
            for result in results
        ),
        "repeated_turn_event_label_groups_per_trial": sorted(
            {
                result["repeated_turn_event_label_groups"]
                for result in results
            }
        ),
    }
    report = {
        "schema_version": "sri.experiment.cross-agent-source-contract.v1",
        "experiment": {
            "name": "cross-agent-official-hook-source-instance-contract",
            "evidence_grade": "Experimental",
            "agents": list(AGENTS),
            "adapter_versions": ADAPTER_VERSIONS,
            "production_hook_builders": True,
            "production_collector_and_storage": True,
            "synthetic_hook_payloads": True,
            "row_level_records_included": False,
            "raw_content_included": False,
            "identifiers_included": False,
            "limitations": [
                "Repeated trials exercise deterministic code paths and are not independent Agent workloads.",
                "Synthetic hooks do not establish live Agent schema compatibility.",
                "Agent-scoped identity does not solve semantic cross-Agent task alignment.",
                "Zero cross-source relationships is a safety result, not a complete correlation view.",
            ],
        },
        "metrics": metrics,
        "gates": {
            "agent_scoped_session_identity": exact_trials == trials,
            "same_agent_stream_is_append_only": (
                metrics["same_agent_append_without_new_session_trials"]
                == trials
            ),
            "no_cross_agent_event_id_collision": (
                metrics["cross_agent_event_identity_collision_trials"] == 0
            ),
            "no_implicit_cross_source_causal_edges": (
                metrics["cross_source_relationship_trials"] == 0
            ),
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "cross-Agent source-instance contract",
        "passed": all(report["gates"].values()) and privacy_passed,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.trials < 1:
        parser.error("--trials must be at least 1")
    report = run_experiment(arguments.trials)
    output = write_report(
        EXPERIMENT_DIR,
        "source-instance-contract",
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
