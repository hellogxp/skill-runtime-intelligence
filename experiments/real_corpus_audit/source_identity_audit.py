#!/usr/bin/env python3
"""Audit physical-source and upstream-session cardinality without row output."""

import argparse
import json
import sys
from collections import Counter
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
from skill_runtime_intelligence.adapters.codex import CodexAdapter


def _source_identity(source: Path, maximum_lines: int = 20) -> str:
    try:
        with source.open(
            "r",
            encoding="utf-8",
            errors="replace",
        ) as handle:
            for line_number, line in enumerate(handle):
                if line_number >= maximum_lines:
                    break
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if (
                    record.get("type") == "session_meta"
                    and isinstance(record.get("payload"), dict)
                ):
                    payload = record["payload"]
                    return str(
                        payload.get("session_id")
                        or payload.get("id")
                        or ""
                    )
    except OSError:
        return ""
    return ""


def run_audit(codex_sessions: Path) -> Dict[str, Any]:
    adapter = CodexAdapter(codex_sessions)
    identities = []
    missing_identity_files = 0
    for source in adapter.session_files():
        identity = _source_identity(source)
        if identity:
            identities.append(identity)
        else:
            missing_identity_files += 1
    multiplicities = Counter(Counter(identities).values())
    source_files = len(identities) + missing_identity_files
    source_identity_count = sum(multiplicities.values())
    duplicate_identity_groups = sum(
        count
        for multiplicity, count in multiplicities.items()
        if multiplicity > 1
    )
    duplicate_identity_files = sum(
        (multiplicity - 1) * count
        for multiplicity, count in multiplicities.items()
        if multiplicity > 1
    )
    metrics = {
        "physical_source_files": source_files,
        "files_with_upstream_identity": len(identities),
        "missing_identity_files": missing_identity_files,
        "upstream_identity_count": source_identity_count,
        "duplicate_identity_groups": duplicate_identity_groups,
        "duplicate_identity_files": duplicate_identity_files,
        "maximum_sources_per_identity": max(multiplicities, default=0),
        "identity_multiplicity_histogram": {
            str(multiplicity): count
            for multiplicity, count in sorted(multiplicities.items())
        },
        "physical_to_upstream_identity_ratio": (
            source_files / source_identity_count
            if source_identity_count
            else None
        ),
    }
    report = {
        "schema_version": "sri.experiment.source-identity-audit.v1",
        "experiment": {
            "name": "privacy-safe-source-identity-cardinality-audit",
            "evidence_grade": "Derived",
            "adapter_version": adapter.version,
            "source_files_read_only": True,
            "maximum_lines_read_per_source": 20,
            "row_level_records_included": False,
            "raw_content_included": False,
            "identifiers_included": False,
            "source_paths_included": False,
            "limitations": [
                "One local corpus does not estimate population prevalence.",
                "Only the first 20 lines are searched for session metadata.",
                "Shared upstream identity does not by itself prove divergence.",
                "Cardinality does not measure SkillRun reconstruction quality.",
            ],
        },
        "metrics": metrics,
        "findings": {
            "upstream_identity_is_not_one_to_one": (
                duplicate_identity_files > 0
            ),
        },
        "gates": {
            "all_sources_expose_identity": (
                source_files > 0 and missing_identity_files == 0
            ),
            "aggregate_only_output": True,
        },
    }
    privacy_passed = not _contains_forbidden_row_data(report)
    report["privacy_audit"] = {
        "forbidden_row_level_fields_absent": privacy_passed,
        "passed": privacy_passed,
    }
    report["gate"] = {
        "name": "privacy-safe source identity audit",
        "passed": all(report["gates"].values()) and privacy_passed,
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--codex-sessions",
        type=Path,
        default=Path("~/.codex/sessions").expanduser(),
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    report = run_audit(arguments.codex_sessions)
    output = write_report(
        EXPERIMENT_DIR,
        "source-identity-audit",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "findings": report["findings"],
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
