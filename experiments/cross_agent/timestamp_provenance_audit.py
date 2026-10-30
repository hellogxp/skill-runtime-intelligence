#!/usr/bin/env python3
"""Audit timestamp provenance capabilities without exporting event records."""

import argparse
import json
import sqlite3
import sys
import tempfile
from datetime import datetime
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
from skill_runtime_intelligence.hook_adapter import (
    SUPPORTED_HOOK_AGENTS,
    build_hook_envelopes,
)
from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.storage import Storage


REQUIRED_CAPABILITIES = (
    "event_timestamp",
    "timestamp_origin",
    "ingestion_timestamp",
    "clock_domain",
    "clock_sync_or_uncertainty",
    "timestamp_precision",
    "source_vs_fallback_marker",
)


def _schema_capabilities(database: Path) -> Dict[str, bool]:
    connection = sqlite3.connect(database)
    try:
        columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(normalized_events)"
            ).fetchall()
        }
    finally:
        connection.close()
    return {
        "event_timestamp": "occurred_at" in columns,
        "timestamp_origin": bool(
            {"timestamp_origin", "timestamp_source"} & columns
        ),
        "ingestion_timestamp": bool(
            {"ingested_at", "observed_at", "received_at"} & columns
        ),
        "clock_domain": bool(
            {"clock_domain", "clock_id", "host_clock"} & columns
        ),
        "clock_sync_or_uncertainty": bool(
            {
                "clock_sync_state",
                "clock_uncertainty_ms",
                "timestamp_uncertainty_ms",
            }
            & columns
        ),
        "timestamp_precision": bool(
            {"timestamp_precision", "timestamp_resolution"} & columns
        ),
        "source_vs_fallback_marker": bool(
            {
                "timestamp_is_fallback",
                "timestamp_source",
                "timestamp_origin",
            }
            & columns
        ),
    }


def _valid_iso8601(value: Any) -> bool:
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return False
    return True


def _hook_behavior(storage: Storage) -> Dict[str, int]:
    explicit = "2026-07-30T05:00:00Z"
    explicit_preserved = 0
    fallback_generated = 0
    fallback_labeled = 0
    normalized_event_count = 0
    for agent in sorted(SUPPORTED_HOOK_AGENTS):
        base = {
            "session_id": "timestamp-audit-session",
            "turn_id": "timestamp-audit-turn",
        }
        explicit_envelopes = build_hook_envelopes(
            agent,
            "SessionStart",
            {**base, "timestamp": explicit},
        )
        fallback_envelopes = build_hook_envelopes(
            agent,
            "SessionStart",
            base,
        )
        if (
            len(explicit_envelopes) == 1
            and explicit_envelopes[0].get("occurred_at") == explicit
        ):
            explicit_preserved += 1
        if (
            len(fallback_envelopes) == 1
            and _valid_iso8601(fallback_envelopes[0].get("occurred_at"))
        ):
            fallback_generated += 1
        if fallback_envelopes and any(
            key in fallback_envelopes[0]
            or key in fallback_envelopes[0].get("source", {})
            or key in fallback_envelopes[0].get("payload", {})
            for key in (
                "timestamp_source",
                "timestamp_origin",
                "timestamp_is_fallback",
            )
        ):
            fallback_labeled += 1
        for envelope in explicit_envelopes + fallback_envelopes:
            bundles = normalize_collector_payload(envelope)
            storage.append_collector_events(bundles)
            normalized_event_count += len(bundles)
    persisted = storage.connection.execute(
        """
        SELECT
            COUNT(*) AS event_count,
            SUM(CASE WHEN ingested_at IS NOT NULL AND ingested_at != '' THEN 1 ELSE 0 END)
                AS ingestion_labeled,
            SUM(CASE WHEN clock_domain != 'unknown' THEN 1 ELSE 0 END)
                AS clock_domain_labeled,
            SUM(CASE WHEN timestamp_precision != 'unknown' THEN 1 ELSE 0 END)
                AS precision_labeled,
            SUM(CASE WHEN clock_uncertainty_ms IS NOT NULL THEN 1 ELSE 0 END)
                AS uncertainty_labeled
        FROM normalized_events
        """
    ).fetchone()
    return {
        "agent_profiles": len(SUPPORTED_HOOK_AGENTS),
        "explicit_source_timestamp_preserved": explicit_preserved,
        "missing_timestamp_fallback_generated": fallback_generated,
        "fallback_provenance_labeled": fallback_labeled,
        "normalized_event_count": normalized_event_count,
        "persisted_event_count": int(persisted["event_count"]),
        "ingestion_timestamp_labeled": int(persisted["ingestion_labeled"]),
        "clock_domain_labeled": int(persisted["clock_domain_labeled"]),
        "timestamp_precision_labeled": int(persisted["precision_labeled"]),
        "clock_uncertainty_labeled": int(persisted["uncertainty_labeled"]),
    }


def run_audit() -> Dict[str, Any]:
    with tempfile.TemporaryDirectory(
        prefix="sri-timestamp-provenance-audit-"
    ) as directory:
        database = Path(directory) / "panorama.db"
        storage = Storage(database)
        try:
            capabilities = _schema_capabilities(database)
            behavior = _hook_behavior(storage)
        finally:
            storage.close()
    capability_count = sum(capabilities.values())
    event_count = behavior["persisted_event_count"]
    report = {
        "schema_version": "sri.experiment.timestamp-provenance-audit.v2",
        "experiment": {
            "name": "cross-agent-timestamp-provenance-capability-audit",
            "evidence_grade": "Derived",
            "temporary_database": True,
            "controlled_hook_behavior_check": True,
            "row_level_records_included": False,
            "timestamp_values_included": False,
            "limitations": [
                "Schema capability does not establish timestamp accuracy.",
                "Generated fallback timestamps are not compared with an external clock.",
                "Hook fixtures do not validate live Agent timestamp schemas.",
                "Capability absence is not evidence that an Agent event occurred at the wrong time.",
                "Schema support and populated labels do not establish synchronized clocks.",
            ],
        },
        "capabilities": capabilities,
        "metrics": {
            "required_capability_count": len(REQUIRED_CAPABILITIES),
            "available_capability_count": capability_count,
            "hook_behavior": behavior,
            "cross_agent_absolute_time_ready": (
                capability_count == len(REQUIRED_CAPABILITIES)
                and event_count > 0
                and behavior["clock_uncertainty_labeled"] == event_count
            ),
        },
        "gate": {
            "name": "privacy-safe timestamp capability audit completed",
            "passed": (
                behavior["explicit_source_timestamp_preserved"]
                == behavior["agent_profiles"]
                and behavior["missing_timestamp_fallback_generated"]
                == behavior["agent_profiles"]
                and behavior["fallback_provenance_labeled"]
                == behavior["agent_profiles"]
                and behavior["persisted_event_count"]
                == behavior["normalized_event_count"]
            ),
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"]["passed"] = (
        report["gate"]["passed"] and privacy_passed
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_audit()
    output = write_report(
        EXPERIMENT_DIR,
        "timestamp-provenance-audit",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "capabilities": report["capabilities"],
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
