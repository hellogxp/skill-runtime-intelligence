#!/usr/bin/env python3
"""Compare two privacy-safe corpus audits without accessing row-level data."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import write_report


def _signatures(report: Dict[str, Any]) -> Dict[Tuple[str, str, str], int]:
    return {
        (
            str(row["code"]),
            str(row["stage"]),
            str(row["evidence_grade"]),
        ): int(row["run_count"])
        for row in report["metrics"]["finding_signatures"]
    }


def _mapping_deltas(
    before: Dict[str, int],
    after: Dict[str, int],
) -> list:
    rows = []
    for key in sorted(set(before) | set(after)):
        old = int(before.get(key, 0))
        new = int(after.get(key, 0))
        if old != new:
            rows.append(
                {
                    "key": key,
                    "before": old,
                    "after": new,
                    "delta": new - old,
                }
            )
    return rows


def _compare(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, Any]:
    before_metrics = before["metrics"]
    after_metrics = after["metrics"]
    count_deltas = {}
    for field in ("run_count", "session_count", "skill_definition_count"):
        old = int(before_metrics[field])
        new = int(after_metrics[field])
        count_deltas[field] = {
            "before": old,
            "after": new,
            "delta": new - old,
            "relative_delta": (new - old) / old if old else None,
        }
    before_signatures = _signatures(before)
    after_signatures = _signatures(after)
    signature_deltas = []
    for signature in sorted(set(before_signatures) | set(after_signatures)):
        old = before_signatures.get(signature, 0)
        new = after_signatures.get(signature, 0)
        signature_deltas.append(
            {
                "code": signature[0],
                "stage": signature[1],
                "evidence_grade": signature[2],
                "before": old,
                "after": new,
                "delta": new - old,
            }
        )
    stable = all(row["delta"] == 0 for row in count_deltas.values()) and all(
        row["delta"] == 0 for row in signature_deltas
    )
    before_manifest = before.get("dataset_manifest", {})
    after_manifest = after.get("dataset_manifest", {})
    event_counter_deltas = {
        field: _mapping_deltas(
            before_metrics.get(field, {}),
            after_metrics.get(field, {}),
        )
        for field in (
            "owned_event_type_counts",
            "owned_event_stage_counts",
            "owned_event_evidence_grade_counts",
        )
    }

    def manifests_match(field: str):
        before_value = before_manifest.get(field)
        after_value = after_manifest.get(field)
        if before_value is None or after_value is None:
            return None
        return before_value == after_value

    return {
        "count_deltas": count_deltas,
        "finding_signature_deltas": signature_deltas,
        "before_readiness_passed": before["readiness"]["passed_count"],
        "after_readiness_passed": after["readiness"]["passed_count"],
        "population_stable_on_aggregate_fields": stable,
        "selected_run_population_fields_stable": stable,
        "owned_event_counter_deltas": event_counter_deltas,
        "manifest_comparison": {
            "exact_snapshot_match": manifests_match("snapshot_sha256"),
            "schema_match": manifests_match("schema_sha256"),
            "privacy_safe_aggregate_match": manifests_match(
                "privacy_safe_aggregate_sha256"
            ),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--before", type=Path, required=True)
    parser.add_argument("--after", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    before = json.loads(arguments.before.read_text(encoding="utf-8"))
    after = json.loads(arguments.after.read_text(encoding="utf-8"))
    source_privacy_passed = all(
        report.get("privacy_audit", {}).get("passed") for report in (before, after)
    )
    comparison = _compare(before, after)
    report = {
        "schema_version": "sri.experiment.real-corpus-drift.v2",
        "experiment": {
            "name": "privacy-safe-real-corpus-aggregate-drift",
            "evidence_grade": "Derived",
            "row_level_records_included": False,
            "limitations": [
                "Aggregate drift cannot identify which runs changed.",
                "The comparison does not establish whether restart, re-indexing, source availability, or retention caused the drift.",
                "Two snapshots do not estimate a population drift rate.",
            ],
        },
        "comparison": comparison,
        "gate": {
            "name": "privacy-safe aggregate comparison completed",
            "passed": source_privacy_passed,
        },
    }
    output = write_report(
        EXPERIMENT_DIR,
        "real-corpus-drift",
        report,
        arguments.output,
    )
    print(json.dumps({"comparison": comparison, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
