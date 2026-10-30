#!/usr/bin/env python3
"""Reveal hidden candidates only after two blinded model annotation runs."""

import argparse
import json
import math
import sys
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


def _signature(findings: list) -> tuple:
    return tuple(sorted((item["code"], item["stage"]) for item in findings))


def _protocol_valid(row: dict) -> bool:
    findings = row.get("findings") or []
    codes = [item.get("code") for item in findings]
    return (
        len(codes) == len(set(codes))
        and all(
            item.get("stage") == "outcome"
            for item in findings
            if item.get("code") in {"run_incomplete", "outcome_unverified"}
        )
    )


def _wilson(successes: int, count: int, z: float = 1.959963984540054) -> list:
    if not count:
        return [0.0, 0.0]
    proportion = successes / count
    denominator = 1 + z * z / count
    center = (proportion + z * z / (2 * count)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / count + z * z / (4 * count * count)) / denominator
    return [max(0.0, center - radius), min(1.0, center + radius)]


def summarize(reference: dict, first: dict, second: dict) -> dict:
    hidden = {case["case_id"]: _signature(case["expected_findings"]) for case in reference["cases"]}
    left = {row["case_id"]: row for row in first["rows"] if row["status"] == "completed"}
    right = {row["case_id"]: row for row in second["rows"] if row["status"] == "completed"}
    rows = []
    for case_id in sorted(hidden):
        left_row, right_row = left.get(case_id), right.get(case_id)
        both = bool(left_row and right_row)
        left_signature = tuple(tuple(item) for item in left_row["signature"]) if left_row else ()
        right_signature = tuple(tuple(item) for item in right_row["signature"]) if right_row else ()
        exact_agreement = both and left_signature == right_signature
        left_protocol_valid = bool(left_row) and _protocol_valid(left_row)
        right_protocol_valid = bool(right_row) and _protocol_valid(right_row)
        consensus = (
            exact_agreement and left_protocol_valid and right_protocol_valid
            and not left_row["abstain"] and not right_row["abstain"]
        )
        rows.append({
            "case_id": case_id,
            "both_completed": both,
            "annotator_exact_agreement": exact_agreement,
            "first_protocol_valid": left_protocol_valid,
            "second_protocol_valid": right_protocol_valid,
            "strict_consensus_available": consensus,
            "strict_consensus_matches_hidden_candidate": consensus and left_signature == hidden[case_id],
            "first_matches_hidden_candidate": bool(left_row) and left_signature == hidden[case_id],
            "second_matches_hidden_candidate": bool(right_row) and right_signature == hidden[case_id],
            "hidden_candidate": hidden[case_id],
            "first_signature": left_signature,
            "second_signature": right_signature,
        })
    both = sum(row["both_completed"] for row in rows)
    agreement = sum(row["annotator_exact_agreement"] for row in rows)
    consensus = sum(row["strict_consensus_available"] for row in rows)
    consensus_match = sum(row["strict_consensus_matches_hidden_candidate"] for row in rows)
    return {
        "rows": rows,
        "summary": {
            "case_count": len(rows),
            "both_completed": both,
            "annotator_exact_agreement": agreement,
            "annotator_exact_agreement_rate": agreement / both if both else 0.0,
            "annotator_exact_agreement_wilson95": _wilson(agreement, both),
            "strict_consensus_cases": consensus,
            "strict_consensus_matches_hidden_candidate": consensus_match,
            "strict_consensus_match_rate": consensus_match / consensus if consensus else 0.0,
            "strict_consensus_match_wilson95": _wilson(consensus_match, consensus),
            "first_matches_hidden_candidate": sum(row["first_matches_hidden_candidate"] for row in rows),
            "second_matches_hidden_candidate": sum(row["second_matches_hidden_candidate"] for row in rows),
            "first_protocol_valid": sum(row["first_protocol_valid"] for row in rows),
            "second_protocol_valid": sum(row["second_protocol_valid"] for row in rows),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--first", type=Path, required=True)
    parser.add_argument("--second", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    reference = json.loads(arguments.reference.read_text(encoding="utf-8"))
    first = json.loads(arguments.first.read_text(encoding="utf-8"))
    second = json.loads(arguments.second.read_text(encoding="utf-8"))
    result = summarize(reference, first, second)
    report = {
        "schema_version": "sri.experiment.blinded-real-trace-double-adjudication.v1",
        "experiment": {
            "name": "post-hoc-reveal-of-two-rule-label-blinded-model-annotations",
            "evidence_grade": "Experimental",
            "reference_sha256": sha256_path(arguments.reference),
            "first_sha256": sha256_path(arguments.first),
            "second_sha256": sha256_path(arguments.second),
            "limitations": [
                "This is independent model adjudication, not human-labeled diagnostic accuracy.",
                "Agreement with hidden deterministic candidates may reflect the shared ontology and explicit evidence schema.",
                "Wilson intervals describe this selected 19-case corpus and do not establish population performance.",
                "Consensus outputs remain Inferred and cannot overwrite deterministic findings.",
            ],
        },
        **result,
        "gate": {"name": "both annotators completed every frozen case", "passed": result["summary"]["both_completed"] == result["summary"]["case_count"]},
    }
    output = write_report(EXPERIMENT_DIR, "blinded-real-trace-double-adjudication", report, arguments.output)
    print(json.dumps({"summary": report["summary"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
