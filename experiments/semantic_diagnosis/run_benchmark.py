#!/usr/bin/env python3
"""Leave-one-out retrieval baselines for semantic diagnosis research."""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.runtime_diagnostics.run_benchmark import (
    _materialize_run,
    _signature,
)
from skill_runtime_intelligence.diagnostics import STAGES, diagnose_skill_run


TOKEN = re.compile(r"[a-z0-9_.-]+")


def _text(case: Dict[str, Any]) -> str:
    run = case["run"]
    fields = [
        case.get("description", ""),
        str(run.get("status", "")),
        str(run.get("session_completeness", "")),
        " ".join(run.get("observed_stages", [])),
        " ".join(run.get("failed_stages", [])),
        " ".join(run.get("unsupported_stages", [])),
    ]
    for event in run.get("events", []):
        fields.extend(
            [
                str(event.get("event_type", "")),
                str(event.get("stage", "")),
                str(event.get("status", "")),
                str(event.get("summary", "")),
            ]
        )
    return " ".join(fields).casefold()


def _tokens(case: Dict[str, Any]) -> Set[str]:
    return set(TOKEN.findall(_text(case)))


def _jaccard(left: Set[str], right: Set[str]) -> float:
    return len(left & right) / len(left | right) if left or right else 0.0


def _set_agreement(left: Set[str], right: Set[str]) -> float:
    return 1.0 if not left and not right else _jaccard(left, right)


def _lifecycle_features(case: Dict[str, Any]) -> Dict[str, Any]:
    run = case["run"]
    return {
        "status": str(run.get("status", "")),
        "completeness": str(run.get("session_completeness", "")),
        "observed_stages": set(run.get("observed_stages", [])),
        "failed_stages": set(run.get("failed_stages", [])),
        "unsupported_stages": set(run.get("unsupported_stages", [])),
        "event_types": {
            str(event.get("event_type", ""))
            for event in run.get("events", [])
            if event.get("event_type")
        },
        "event_stages": {
            str(event.get("stage", ""))
            for event in run.get("events", [])
            if event.get("stage")
        },
    }


def _lifecycle_similarity(left: Dict[str, Any], right: Dict[str, Any]) -> float:
    components = [
        (0.5, float(left["status"] == right["status"])),
        (0.5, float(left["completeness"] == right["completeness"])),
        (
            1.5,
            _set_agreement(
                left["observed_stages"],
                right["observed_stages"],
            ),
        ),
        (
            4.0,
            _set_agreement(left["failed_stages"], right["failed_stages"]),
        ),
        (
            1.5,
            _set_agreement(
                left["unsupported_stages"],
                right["unsupported_stages"],
            ),
        ),
        (
            2.0,
            _set_agreement(left["event_types"], right["event_types"]),
        ),
        (
            2.0,
            _set_agreement(left["event_stages"], right["event_stages"]),
        ),
    ]
    return sum(weight * value for weight, value in components) / sum(
        weight for weight, _ in components
    )


def _relational_anchors(case: Dict[str, Any]) -> Dict[str, Tuple[str, str]]:
    """Extract ordered evidence relations without assigning finding codes."""
    run = case["run"]
    observed = set(run.get("observed_stages", []))
    failed = set(run.get("failed_stages", []))
    unsupported = set(run.get("unsupported_stages", []))
    anchors: Dict[str, Tuple[str, str]] = {}

    failed_events = [
        event
        for event in run.get("events", [])
        if event.get("status") == "failed" and event.get("stage") in STAGES
    ]
    if failed_events:
        first_failed_stage = min(
            (str(event["stage"]) for event in failed_events),
            key=STAGES.index,
        )
        grade = (
            "observed"
            if any(
                event.get("stage") == first_failed_stage
                and event.get("evidence_grade") == "observed"
                for event in failed_events
            )
            else "derived"
        )
        anchors["first_failed_stage"] = (first_failed_stage, grade)

    stage_states = []
    for stage in STAGES:
        if stage in unsupported:
            state = "unsupported"
        elif stage in failed:
            state = "failed"
        elif stage in observed:
            state = "observed"
        else:
            state = "not_observed"
        stage_states.append((stage, state))
    for index, (stage, state) in enumerate(stage_states):
        if state != "not_observed":
            continue
        if any(
            later_state in {"observed", "failed"}
            for _, later_state in stage_states[index + 1 :]
        ):
            anchors["first_supported_gap_before_later_activity"] = (
                stage,
                "derived",
            )
            break

    incomplete = (
        run.get("status") in {"incomplete", "interrupted"}
        or run.get("session_completeness") in {"incomplete", "partial"}
    )
    if incomplete:
        anchors["incomplete_or_partial"] = ("outcome", "observed")

    outcome_events = [
        event
        for event in run.get("events", [])
        if event.get("stage") == "outcome"
    ]
    if (
        outcome_events
        and not incomplete
        and not any(
            event.get("event_type") == "outcome.verified"
            for event in outcome_events
        )
    ):
        anchors["reported_outcome_without_verifier"] = ("outcome", "derived")
    return anchors


def _relational_template_prediction(
    case: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> Tuple[Set[Tuple[str, str, str]], List[Dict[str, Any]]]:
    """Learn finding-code templates from other cases and bind query anchors.

    A template is selected only when its positive support is strictly greater
    than both null support and every competing code. This keeps the leave-one-
    out baseline conservative when a relation has not been labeled elsewhere.
    """
    support: Dict[str, Counter] = defaultdict(Counter)
    sources: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for candidate in candidates:
        expected = _expected(candidate)
        for relation, (stage, grade) in _relational_anchors(candidate).items():
            matching_codes = sorted(
                code
                for code, finding_stage, finding_grade in expected
                if finding_stage == stage and finding_grade == grade
            )
            code = matching_codes[0] if len(matching_codes) == 1 else "__none__"
            support[relation][code] += 1
            sources[(relation, code)].append(candidate["case_id"])

    prediction: Set[Tuple[str, str, str]] = set()
    audit = []
    for relation, (stage, grade) in _relational_anchors(case).items():
        counts = support.get(relation, Counter())
        positive = [
            (count, code)
            for code, count in counts.items()
            if code != "__none__"
        ]
        positive.sort(reverse=True)
        selected_code = None
        if positive:
            best_count, best_code = positive[0]
            next_count = positive[1][0] if len(positive) > 1 else 0
            if best_count > counts.get("__none__", 0) and best_count > next_count:
                selected_code = best_code
                prediction.add((best_code, stage, grade))
        audit.append(
            {
                "relation": relation,
                "stage": stage,
                "evidence_grade": grade,
                "selected_code": selected_code,
                "positive_support": {
                    code: count
                    for code, count in sorted(counts.items())
                    if code != "__none__"
                },
                "null_support": counts.get("__none__", 0),
                "source_case_ids": (
                    sources.get((relation, selected_code), [])
                    if selected_code
                    else []
                ),
            }
        )
    return prediction, audit


def _expected(case: Dict[str, Any]) -> Set[Tuple[str, str, str]]:
    return {_signature(item) for item in case["expected_findings"]}


def _metrics(pairs: Iterable[Tuple[Set[tuple], Set[tuple]]]) -> Dict[str, Any]:
    tp = fp = fn = exact = count = 0
    for expected, actual in pairs:
        count += 1
        tp += len(expected & actual)
        fp += len(actual - expected)
        fn += len(expected - actual)
        exact += expected == actual
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "case_count": count,
        "exact_matches": exact,
        "exact_match_rate": exact / count,
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=REPOSITORY_ROOT
        / "experiments"
        / "runtime_diagnostics"
        / "cases.jsonl",
    )
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    cases = load_jsonl(arguments.cases)
    token_sets = {case["case_id"]: _tokens(case) for case in cases}
    lifecycle_features = {
        case["case_id"]: _lifecycle_features(case) for case in cases
    }
    rows = []
    deterministic_pairs = []
    retrieval_pairs = []
    lifecycle_retrieval_pairs = []
    relational_template_pairs = []
    for case in cases:
        candidates = [candidate for candidate in cases if candidate is not case]
        neighbor = max(
            candidates,
            key=lambda candidate: (
                _jaccard(
                    token_sets[case["case_id"]],
                    token_sets[candidate["case_id"]],
                ),
                candidate["case_id"],
            ),
        )
        lifecycle_neighbor = max(
            candidates,
            key=lambda candidate: (
                _lifecycle_similarity(
                    lifecycle_features[case["case_id"]],
                    lifecycle_features[candidate["case_id"]],
                ),
                candidate["case_id"],
            ),
        )
        expected = _expected(case)
        retrieved = _expected(neighbor)
        lifecycle_retrieved = _expected(lifecycle_neighbor)
        relational_retrieved, relational_template_audit = (
            _relational_template_prediction(case, candidates)
        )
        deterministic = {
            _signature(item)
            for item in diagnose_skill_run(_materialize_run(case["run"]))
        }
        deterministic_pairs.append((expected, deterministic))
        retrieval_pairs.append((expected, retrieved))
        lifecycle_retrieval_pairs.append((expected, lifecycle_retrieved))
        relational_template_pairs.append((expected, relational_retrieved))
        rows.append(
            {
                "case_id": case["case_id"],
                "nearest_case_id": neighbor["case_id"],
                "similarity": _jaccard(
                    token_sets[case["case_id"]],
                    token_sets[neighbor["case_id"]],
                ),
                "prediction_grade": "inferred",
                "expected": sorted(expected),
                "deterministic": sorted(deterministic),
                "lexical_retrieval": sorted(retrieved),
                "deterministic_exact": deterministic == expected,
                "retrieval_exact": retrieved == expected,
                "lifecycle_nearest_case_id": lifecycle_neighbor["case_id"],
                "lifecycle_similarity": _lifecycle_similarity(
                    lifecycle_features[case["case_id"]],
                    lifecycle_features[lifecycle_neighbor["case_id"]],
                ),
                "lifecycle_prediction_grade": "inferred",
                "lifecycle_retrieval": sorted(lifecycle_retrieved),
                "lifecycle_retrieval_exact": lifecycle_retrieved == expected,
                "relational_template_prediction_grade": "inferred",
                "relational_template_retrieval": sorted(relational_retrieved),
                "relational_template_retrieval_exact": (
                    relational_retrieved == expected
                ),
                "relational_template_audit": relational_template_audit,
            }
        )
    deterministic_metrics = _metrics(deterministic_pairs)
    retrieval_metrics = _metrics(retrieval_pairs)
    lifecycle_retrieval_metrics = _metrics(lifecycle_retrieval_pairs)
    relational_template_metrics = _metrics(relational_template_pairs)
    separation_gate = (
        all(row["prediction_grade"] == "inferred" for row in rows)
        and all(
            row["lifecycle_prediction_grade"] == "inferred" for row in rows
        )
        and all(
            row["relational_template_prediction_grade"] == "inferred"
            for row in rows
        )
        and deterministic_metrics["exact_match_rate"] == 1.0
    )
    report = {
        "schema_version": "sri.experiment.semantic-diagnosis.v4",
        "experiment": {
            "name": "leave-one-out-diagnosis-relational-ablation",
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "limitations": [
                "This is a lexical retrieval lower bound, not an LLM diagnosis result.",
                "Lifecycle-aware retrieval is a structured-feature ablation, not a semantic model.",
                "Failed-stage features are close to deterministic labels and can overstate retrieval generalization.",
                "Relational anchors are close to production rule predicates; this ablation measures representation and template coverage, not an independent intelligent diagnostician.",
                "The relational template baseline cannot emit a finding code absent from its leave-one-out training cases.",
                "The small synthetic corpus cannot estimate deployment generalization.",
                "Retrieved predictions are Inferred and never mutate deterministic findings.",
            ],
        },
        "deterministic_rules": deterministic_metrics,
        "lexical_retrieval": retrieval_metrics,
        "lifecycle_retrieval": lifecycle_retrieval_metrics,
        "relational_template_retrieval": relational_template_metrics,
        "rows": rows,
        "gate": {
            "name": "inference-layer separation",
            "passed": separation_gate,
        },
    }
    output = write_report(
        EXPERIMENT_DIR, "semantic-diagnosis", report, arguments.output
    )
    print(
        json.dumps(
            {
                "deterministic_rules": deterministic_metrics,
                "lexical_retrieval": retrieval_metrics,
                "lifecycle_retrieval": lifecycle_retrieval_metrics,
                "relational_template_retrieval": relational_template_metrics,
                "separation_gate": separation_gate,
            },
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if separation_gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
