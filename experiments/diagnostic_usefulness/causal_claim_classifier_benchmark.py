#!/usr/bin/env python3
"""Evaluate a fail-closed causal-claim classifier on adversarial phrases."""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from skill_runtime_intelligence.diagnostics import (
    CAUSAL_CLAIM_KINDS,
    validate_causal_claim,
)


_EVIDENCE_BOUNDARY_PATTERNS = (
    r"\bno evidence that\b",
    r"\bnot evidence of causation\b",
    r"\bdoes not prove\b",
    r"\bcannot establish\b",
    r"\bcannot answer\b",
    r"\bremains unknown whether\b",
    r"\brequired before estimating\b",
)
_NON_ASSERTIVE_PATTERNS = (
    r"^\s*did\b.*\bcause\b",
    r"^\s*if\b.*\bcaused?\b",
)
_SOURCE_PATTERNS = (
    r"\b(?:agent|source|model)\s+(?:reported|asserted|claimed)\b",
    r"\baccording to (?:the )?(?:agent|source|model)\b",
    r"\blog records the message\b",
)
_EFFECT_PATTERNS = (
    r"\bcaused?\b",
    r"\bled to\b",
    r"\bresulted in\b",
    r"\bresponsible for\b",
    r"\bbecause of\b",
    r"\bhad no effect\b",
    r"\bimproved\b",
    r"\bincreased\b",
    r"\bprevented\b",
    r"\bmade\b.*\bfail\b",
    r"\boutcome increase\b",
)
_V3_EVIDENCE_BOUNDARY_PATTERNS = (
    r"\bno causal conclusion\b",
    r"\bcannot infer causality\b",
    r"\bmore evidence is required\b",
    r"\bcompatible with many possible causes\b",
)
_V3_SOURCE_PATTERNS = (
    r"\bper the runtime\b",
    r"\breport quotes the agent\b",
    r"\bevaluator wrote\b",
    r"\bsource-side field attributes\b",
    r"声称",
)
_V3_EFFECT_PATTERNS = (
    r"\bbrought about\b",
    r"\bwould not have occurred\b",
    r"\bis why\b",
    r"\bcontributed to\b",
    r"\bneither improved nor harmed\b",
    r"导致",
    r"提高",
)


def _matches_any(patterns: tuple[str, ...], text: str) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def classify_claim(text: str) -> Dict[str, str]:
    """Pattern-v1 classifier retained for reproducible baseline comparison."""
    normalized = " ".join(text.lower().split())
    if _matches_any(_EVIDENCE_BOUNDARY_PATTERNS, normalized):
        kind = "descriptive"
        basis = "evidence-boundary language"
    elif _matches_any(_NON_ASSERTIVE_PATTERNS, normalized):
        kind = "descriptive"
        basis = "question or conditional language"
    elif _matches_any(_SOURCE_PATTERNS, normalized):
        kind = "source_attribution"
        basis = "explicit source-attribution language"
    elif _matches_any(_EFFECT_PATTERNS, normalized):
        kind = "skill_outcome_effect"
        basis = "causal-effect language"
    else:
        kind = "descriptive"
        basis = "no causal or source-attribution pattern"
    return {"claim_kind": kind, "basis": basis}


def classify_claim_fail_closed(text: str) -> Dict[str, str]:
    """Return unknown instead of assuming unrecognized wording is descriptive."""
    result = classify_claim(text)
    if result["basis"] == "no causal or source-attribution pattern":
        return {
            "claim_kind": "unknown",
            "basis": "unrecognized wording; fail-closed abstention",
        }
    return result


def classify_claim_fail_closed_v3(text: str) -> Dict[str, str]:
    """Frozen deny-only verifier derived from the first challenge failures."""
    normalized = " ".join(text.lower().split())
    if _matches_any(_V3_EVIDENCE_BOUNDARY_PATTERNS, normalized):
        return {
            "claim_kind": "descriptive",
            "basis": "v3 evidence-boundary language",
        }
    if _matches_any(_V3_SOURCE_PATTERNS, normalized):
        return {
            "claim_kind": "source_attribution",
            "basis": "v3 source-attribution language",
        }
    if _matches_any(_V3_EFFECT_PATTERNS, normalized):
        return {
            "claim_kind": "skill_outcome_effect",
            "basis": "v3 causal-effect language",
        }
    return classify_claim_fail_closed(text)


def _classification_metrics(rows: list[dict]) -> dict:
    per_class = {}
    for kind in CAUSAL_CLAIM_KINDS:
        true_positive = sum(
            row["expected_claim_kind"] == kind
            and row["predicted_claim_kind"] == kind
            for row in rows
        )
        false_positive = sum(
            row["expected_claim_kind"] != kind
            and row["predicted_claim_kind"] == kind
            for row in rows
        )
        false_negative = sum(
            row["expected_claim_kind"] == kind
            and row["predicted_claim_kind"] != kind
            for row in rows
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        per_class[kind] = {
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": (
                2 * precision * recall / (precision + recall)
                if precision + recall
                else 0.0
            ),
        }
    exact = sum(
        row["expected_claim_kind"] == row["predicted_claim_kind"]
        for row in rows
    )
    return {
        "case_count": len(rows),
        "exact_matches": exact,
        "exact_match_rate": exact / len(rows) if rows else 0.0,
        "guard_decision_exact": sum(
            row["expected_allowed"] == row["predicted_allowed"]
            for row in rows
        ),
        "false_allows": sum(
            not row["expected_allowed"] and row["predicted_allowed"]
            for row in rows
        ),
        "false_denies": sum(
            row["expected_allowed"] and not row["predicted_allowed"]
            for row in rows
        ),
        "class_counts": dict(
            sorted(Counter(row["expected_claim_kind"] for row in rows).items())
        ),
        "per_class": per_class,
    }


def run_benchmark(
    cases_path: Path,
    corpus_role: str = "development-contract",
    classifier_policy: str = "pattern-v1",
) -> dict:
    cases = load_jsonl(cases_path)
    rows = []
    classifiers = {
        "pattern-v1": classify_claim,
        "fail-closed-v2": classify_claim_fail_closed,
        "fail-closed-v3": classify_claim_fail_closed_v3,
    }
    classifier = classifiers[classifier_policy]
    for case in cases:
        predicted = classifier(case["text"])
        guard = validate_causal_claim(
            case["causal_scope"], predicted["claim_kind"]
        )
        expected_guard = validate_causal_claim(
            case["causal_scope"], case["expected_claim_kind"]
        )
        if expected_guard["allowed"] != case["expected_allowed"]:
            raise ValueError(
                f"{case['case_id']}: expected_allowed conflicts with scope policy"
            )
        rows.append(
            {
                "case_id": case["case_id"],
                "tags": case["tags"],
                "causal_scope": case["causal_scope"],
                "expected_claim_kind": case["expected_claim_kind"],
                "predicted_claim_kind": predicted["claim_kind"],
                "classifier_basis": predicted["basis"],
                "expected_allowed": case["expected_allowed"],
                "predicted_allowed": guard["allowed"],
            }
        )
    metrics = _classification_metrics(rows)
    passed = (
        metrics["exact_matches"] == metrics["case_count"]
        and metrics["guard_decision_exact"] == metrics["case_count"]
        and metrics["false_allows"] == 0
        and metrics["false_denies"] == 0
    )
    return {
        "schema_version": "sri.experiment.causal-claim-classifier.v1",
        "experiment": {
            "name": "adversarial-causal-claim-classifier-contract",
            "evidence_grade": "derived",
            "corpus_role": corpus_role,
            "classifier_policy": classifier_policy,
            "dataset_path": str(cases_path.resolve()),
            "dataset_sha256": sha256_path(cases_path),
            "limitations": [
                (
                    "The development corpus and classifier were developed together; exact match is a contract check, not a generalization estimate."
                    if corpus_role == "development-contract"
                    else "The post-freeze challenge is hand-authored and small; it is a targeted robustness probe, not a population estimate."
                ),
                "The corpus contains short isolated sentences and may not represent deployment language.",
                "Pattern matching does not resolve discourse, sarcasm, nested quotation, or multilingual claims.",
                "The classifier may only restrict a claim; it must never expand a Finding causal scope.",
            ],
        },
        "metrics": metrics,
        "cases": rows,
        "gates": {
            "classification_contract_exact": (
                metrics["exact_matches"] == metrics["case_count"]
            ),
            "guard_safety_no_false_allow": metrics["false_allows"] == 0,
            "guard_usability_no_false_deny": metrics["false_denies"] == 0,
        },
        "gate": {"name": "causal-claim classifier contract", "passed": passed},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=EXPERIMENT_DIR / "causal_claim_cases.jsonl",
    )
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--corpus-role",
        default="development-contract",
        choices=("development-contract", "post-freeze-challenge"),
    )
    parser.add_argument(
        "--classifier-policy",
        default="pattern-v1",
        choices=("pattern-v1", "fail-closed-v2", "fail-closed-v3"),
    )
    arguments = parser.parse_args()
    report = run_benchmark(
        arguments.cases,
        arguments.corpus_role,
        arguments.classifier_policy,
    )
    output = write_report(
        EXPERIMENT_DIR,
        "causal-claim-classifier",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": report["metrics"],
                "gates": report["gates"],
                "gate_passed": report["gate"]["passed"],
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
