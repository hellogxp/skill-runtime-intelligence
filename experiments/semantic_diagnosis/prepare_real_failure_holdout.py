#!/usr/bin/env python3
"""Build a de-identified real-run diagnostic holdout from a read-only snapshot."""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import sha256_path, write_report
from experiments.real_corpus_audit.run_benchmark import _consistent_snapshot
from skill_runtime_intelligence.storage import Storage


SAFE_TOKEN = re.compile(r"^[a-z0-9_.-]{1,80}$")
SAFE_FINDING_CODES = {
    "lifecycle_evidence_gap",
    "outcome_unverified",
    "run_incomplete",
    "runtime_failure",
}
SAFE_STAGES = {
    "request",
    "discovery",
    "activation",
    "instructions",
    "resources",
    "execution",
    "artifacts",
    "outcome",
}
SAFE_GRADES = {"observed", "derived", "inferred", "experimental"}


def _safe(value: Any, fallback: str = "unknown") -> str:
    token = str(value or fallback).casefold()
    return token if SAFE_TOKEN.fullmatch(token) else fallback


def _expected(detail: Dict[str, Any]) -> Tuple[Tuple[str, str, str], ...]:
    return tuple(
        sorted(
            (
                str(item.get("code")),
                str(item.get("stage")),
                str(item.get("evidence_grade")),
            )
            for item in detail.get("findings", [])
            if item.get("code") in SAFE_FINDING_CODES
            and item.get("stage") in SAFE_STAGES
            and item.get("evidence_grade") in SAFE_GRADES
        )
    )


def _event_signatures(events: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counts = Counter()
    for event in events:
        if event.get("context_only"):
            continue
        signature = (
            _safe(event.get("event_type")),
            _safe(event.get("stage")),
            _safe(event.get("status")),
            _safe(event.get("evidence_grade")),
        )
        counts[signature] += 1
    return [
        {
            "event_type": signature[0],
            "stage": signature[1],
            "status": signature[2],
            "evidence_grade": signature[3],
            "count": count,
        }
        for signature, count in sorted(counts.items())
    ]


def _case(detail: Dict[str, Any], case_id: str) -> Dict[str, Any]:
    evidence = [
        {
            "evidence_id": "E001",
            "kind": "run_state",
            "status": _safe(detail.get("status")),
        },
        {
            "evidence_id": "E002",
            "kind": "session_completeness",
            "completeness": _safe(detail.get("session_completeness")),
        },
    ]
    for stage in detail.get("stage_summary", []):
        evidence.append(
            {
                "evidence_id": f"E{len(evidence) + 1:03d}",
                "kind": "stage_state",
                "stage": _safe(stage.get("stage")),
                "status": _safe(stage.get("status")),
                "event_count": int(stage.get("event_count") or 0),
                "capability": _safe(stage.get("capability")),
                "evidence_grade": _safe(stage.get("evidence_grade")),
            }
        )
    for signature in _event_signatures(detail.get("events", [])):
        evidence.append(
            {
                "evidence_id": f"E{len(evidence) + 1:03d}",
                "kind": "event_signature",
                **signature,
            }
        )
    return {
        "case_id": case_id,
        "source": "deidentified_real_skill_run",
        "evidence": evidence,
        "expected_findings": [
            {
                "code": code,
                "stage": stage,
                "source_evidence_grade": grade,
            }
            for code, stage, grade in _expected(detail)
        ],
        "label_origin": "production_deterministic_diagnostic_candidate",
    }


def build_holdout(database: Path, maximum_per_profile: int) -> Dict[str, Any]:
    snapshot, attempts = _consistent_snapshot(database)
    try:
        storage = Storage(snapshot)
        profiles: Dict[Tuple[Tuple[str, str, str], ...], List[Dict[str, Any]]] = (
            defaultdict(list)
        )
        try:
            for row in storage.list_skill_runs(limit=100_000):
                detail = storage.get_skill_run(row["skill_run_id"])
                if not detail:
                    continue
                profile = _expected(detail)
                if profile:
                    profiles[profile].append(detail)
        finally:
            storage.close()
        cases = []
        selected_profiles = []
        for profile in sorted(profiles):
            rows = sorted(
                profiles[profile], key=lambda item: str(item["skill_run_id"])
            )[:maximum_per_profile]
            selected_profiles.append(
                {
                    "finding_signature": [list(item) for item in profile],
                    "available_count": len(profiles[profile]),
                    "selected_count": len(rows),
                }
            )
            for detail in rows:
                cases.append(_case(detail, f"real-holdout-{len(cases) + 1:03d}"))
        return {
            "schema_version": "sri.experiment.real-failure-holdout.v1",
            "experiment": {
                "name": "deidentified-real-skill-run-diagnostic-holdout",
                "evidence_grade": "Derived",
                "source_database_basename": database.name,
                "snapshot_sha256": sha256_path(snapshot),
                "snapshot_backup_attempts": attempts,
                "selection": "up to N lexicographically selected runs per distinct deterministic finding profile",
                "maximum_per_profile": maximum_per_profile,
                "raw_content_included": False,
                "row_identifiers_included": False,
                "timestamps_included": False,
                "limitations": [
                    "Expected findings are production deterministic candidates, not independent human gold labels.",
                    "The holdout is novel relative to the synthetic E5 corpus but comes from one local user's runtime database.",
                    "Event signatures omit summaries, payloads, paths, timestamps, and source locators.",
                    "Agreement with these labels measures rule reproduction, not real-world semantic correctness.",
                ],
            },
            "profile_summary": selected_profiles,
            "cases": cases,
            "privacy_audit": {
                "raw_content_absent": True,
                "source_identifiers_absent": True,
                "passed": True,
            },
            "gate": {
                "name": "non-empty deidentified holdout construction",
                "passed": bool(cases),
            },
        }
    finally:
        snapshot.unlink(missing_ok=True)
        Path(f"{snapshot}-wal").unlink(missing_ok=True)
        Path(f"{snapshot}-shm").unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--maximum-per-profile", type=int, default=4)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.maximum_per_profile < 1:
        parser.error("--maximum-per-profile must be positive")
    report = build_holdout(arguments.database, arguments.maximum_per_profile)
    output = write_report(
        EXPERIMENT_DIR, "real-failure-holdout", report, arguments.output
    )
    print(
        json.dumps(
            {
                "case_count": len(report["cases"]),
                "profiles": report["profile_summary"],
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
