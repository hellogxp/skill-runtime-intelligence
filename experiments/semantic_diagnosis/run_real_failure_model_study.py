#!/usr/bin/env python3
"""Compare an ordered graph baseline with an evidence-citing model on real runs."""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, Set, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report


STAGES = (
    "request",
    "discovery",
    "activation",
    "instructions",
    "resources",
    "execution",
    "artifacts",
    "outcome",
)
FINDING_CODES = (
    "lifecycle_evidence_gap",
    "outcome_unverified",
    "run_incomplete",
    "runtime_failure",
)
GRADES = ("observed", "derived")
Signature = Tuple[str, str, str]


def _signature(item: Dict[str, Any]) -> Signature:
    return (
        str(item.get("code")),
        str(item.get("stage")),
        str(item.get("source_evidence_grade")),
    )


def _citation_entails(
    finding: Dict[str, Any], evidence: Iterable[Dict[str, Any]]
) -> bool:
    """Require cited rows to contain the relation asserted by a finding."""
    by_id = {str(item.get("evidence_id")): item for item in evidence}
    citations = finding.get("citations")
    if not isinstance(citations, list) or not citations:
        return False
    cited = [by_id.get(str(identifier)) for identifier in citations]
    if any(item is None for item in cited):
        return False
    code = finding.get("code")
    stage = finding.get("stage")
    grade = finding.get("source_evidence_grade")
    if code == "runtime_failure":
        failures = [item for item in cited if item.get("kind") == "event_signature"
                    and item.get("stage") == stage and item.get("status") == "failed"]
        if not failures:
            return False
        expected_grade = "observed" if any(item.get("evidence_grade") == "observed" for item in failures) else "derived"
        return grade == expected_grade
    if code == "run_incomplete":
        asserted = any(
            (item.get("kind") == "run_state" and item.get("status") in {"incomplete", "interrupted"})
            or (item.get("kind") == "session_completeness" and item.get("completeness") in {"incomplete", "partial"})
            for item in cited
        )
        return asserted and stage == "outcome" and grade == "observed"
    if code == "lifecycle_evidence_gap":
        missing = [item for item in cited if item.get("kind") == "stage_state"
                   and item.get("stage") == stage and item.get("status") == "not_observed"]
        later = [item for item in cited if item.get("kind") == "stage_state"
                 and item.get("stage") in STAGES and item.get("status") in {"observed", "failed"}
                 and stage in STAGES and STAGES.index(item.get("stage")) > STAGES.index(stage)]
        return bool(missing and later) and grade == "derived"
    if code == "outcome_unverified":
        reported = any(item.get("kind") == "event_signature" and item.get("stage") == "outcome"
                       and item.get("event_type") != "outcome.verified" for item in cited)
        verifier_expected = any(item.get("kind") == "verifier_expectation"
                                and item.get("verifier_expected") is True for item in cited)
        return reported and verifier_expected and stage == "outcome" and grade == "derived"
    return False


def _entailment_valid(
    findings: Iterable[Dict[str, Any]], evidence: Iterable[Dict[str, Any]]
) -> bool:
    return all(_citation_entails(item, evidence) for item in findings)


def _graph_baseline(case: Dict[str, Any]) -> Dict[str, Any]:
    evidence = case["evidence"]
    run = next(item for item in evidence if item["kind"] == "run_state")
    completeness = next(
        item for item in evidence if item["kind"] == "session_completeness"
    )
    stage_rows = {
        item["stage"]: item
        for item in evidence
        if item["kind"] == "stage_state" and item.get("stage") in STAGES
    }
    event_rows = [item for item in evidence if item["kind"] == "event_signature"]
    findings = []
    failed = [
        item
        for item in event_rows
        if item.get("status") == "failed" and item.get("stage") in STAGES
    ]
    if failed:
        stage = min((item["stage"] for item in failed), key=STAGES.index)
        stage_failed = [item for item in failed if item["stage"] == stage]
        findings.append(
            {
                "code": "runtime_failure",
                "stage": stage,
                "source_evidence_grade": (
                    "observed"
                    if any(item.get("evidence_grade") == "observed" for item in stage_failed)
                    else "derived"
                ),
                "citations": [item["evidence_id"] for item in stage_failed],
            }
        )
    if run.get("status") in {"incomplete", "interrupted"} or completeness.get(
        "completeness"
    ) in {"incomplete", "partial"}:
        findings.append(
            {
                "code": "run_incomplete",
                "stage": "outcome",
                "source_evidence_grade": "observed",
                "citations": [run["evidence_id"], completeness["evidence_id"]],
            }
        )
    ordered = [stage_rows[stage] for stage in STAGES if stage in stage_rows]
    for index, item in enumerate(ordered):
        if item.get("status") != "not_observed":
            continue
        later = [
            row
            for row in ordered[index + 1 :]
            if row.get("status") in {"observed", "failed"}
        ]
        if later:
            findings.append(
                {
                    "code": "lifecycle_evidence_gap",
                    "stage": item["stage"],
                    "source_evidence_grade": "derived",
                    "citations": [item["evidence_id"], later[0]["evidence_id"]],
                }
            )
            break
    return {"findings": findings, "inference_grade": "inferred"}


def _prompt(case: Dict[str, Any]) -> str:
    return (
        "Diagnose this de-identified Skill runtime evidence graph. Use only the supplied evidence. "
        "Return runtime_failure for the earliest explicit failed lifecycle stage; run_incomplete "
        "when run status is incomplete/interrupted or session completeness is incomplete/partial; "
        "and lifecycle_evidence_gap for the first not_observed stage before later observed/failed "
        "activity. Do not infer that a missing event means an action did not occur. Every finding "
        "must cite one or more exact evidence_id values. The evidence cannot prove that the Skill "
        "caused the final outcome, so causal_proven must be false. Return no prose.\nEvidence:\n"
        + json.dumps(case["evidence"], ensure_ascii=False, sort_keys=True)
    )


def _schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "enum": list(FINDING_CODES)},
                        "stage": {"type": "string", "enum": list(STAGES)},
                        "source_evidence_grade": {"type": "string", "enum": list(GRADES)},
                        "citations": {
                            "type": "array",
                            "items": {"type": "string"},
                            "minItems": 1,
                        },
                    },
                    "required": ["code", "stage", "source_evidence_grade", "citations"],
                    "additionalProperties": False,
                },
            },
            "causal_proven": {"type": "boolean"},
            "confidence_0_100": {"type": "number", "minimum": 0, "maximum": 100},
        },
        "required": ["findings", "causal_proven", "confidence_0_100"],
        "additionalProperties": False,
    }


def _run_case(
    case: Dict[str, Any], api_base: str, model: str, timeout: float, max_tokens: int,
    enable_thinking: bool,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "Return only a JSON object matching the schema."},
            {"role": "user", "content": _prompt(case)},
        ],
        "temperature": 0,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": "sri_real_failure_diagnosis", "strict": True, "schema": _schema()},
        },
    }
    request = urllib.request.Request(
        api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            envelope = json.load(response)
        parsed = json.loads(envelope["choices"][0]["message"]["content"])
        elapsed_ms = (time.perf_counter() - started) * 1000
    except (OSError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError, urllib.error.HTTPError, urllib.error.URLError) as error:
        detail = ""
        if isinstance(error, urllib.error.HTTPError):
            try:
                detail = error.read().decode("utf-8", errors="replace")[:500]
            except OSError:
                detail = ""
        return {
            "case_id": case["case_id"],
            "status": "execution_error",
            "error": type(error).__name__,
            "error_detail": detail,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
        }
    valid_ids = {item["evidence_id"] for item in case["evidence"]}
    findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
    citation_valid = all(
        isinstance(item.get("citations"), list)
        and bool(item["citations"])
        and set(item["citations"]) <= valid_ids
        for item in findings
        if isinstance(item, dict)
    ) and all(isinstance(item, dict) for item in findings)
    citation_entailment_valid = citation_valid and _entailment_valid(
        findings, case["evidence"]
    )
    expected = {_signature(item) for item in case["expected_findings"]}
    predicted = {_signature(item) for item in findings}
    return {
        "case_id": case["case_id"],
        "status": "completed",
        "expected": sorted(expected),
        "predicted": sorted(predicted),
        "predicted_findings": findings,
        "exact": predicted == expected,
        "citation_valid": citation_valid,
        "citation_entailment_valid": citation_entailment_valid,
        "causal_proven": parsed.get("causal_proven"),
        "causal_safe": parsed.get("causal_proven") is False,
        "confidence_0_100": parsed.get("confidence_0_100"),
        "elapsed_ms": elapsed_ms,
        "inference_grade": "inferred",
        "usage": envelope.get("usage") or {},
    }


def _set_metrics(pairs: Iterable[Tuple[Set[Signature], Set[Signature]]]) -> Dict[str, Any]:
    count = exact = tp = fp = fn = 0
    for expected, predicted in pairs:
        count += 1
        exact += expected == predicted
        tp += len(expected & predicted)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {
        "case_count": count,
        "exact_matches": exact,
        "exact_match_rate": exact / count if count else 0.0,
        "precision": precision,
        "recall": recall,
        "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--model", required=True)
    parser.add_argument("--server-version", default="unknown")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--max-tokens", type=int, default=512)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    holdout = json.loads(arguments.cases.read_text(encoding="utf-8"))
    cases = holdout["cases"]
    graph_rows = []
    for case in cases:
        prediction = _graph_baseline(case)
        expected = {_signature(item) for item in case["expected_findings"]}
        actual = {_signature(item) for item in prediction["findings"]}
        graph_rows.append(
            {
                "case_id": case["case_id"],
                "expected": sorted(expected),
                "predicted": sorted(actual),
                "exact": expected == actual,
                "citation_valid": all(item["citations"] for item in prediction["findings"]),
                "citation_entailment_valid": _entailment_valid(
                    prediction["findings"], case["evidence"]
                ),
                "inference_grade": "inferred",
            }
        )
    model_rows = []
    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [
            executor.submit(
                _run_case,
                case,
                arguments.api_base,
                arguments.model,
                arguments.timeout_seconds,
                arguments.max_tokens,
                arguments.enable_thinking,
            )
            for case in cases
        ]
        for future in as_completed(futures):
            model_rows.append(future.result())
    model_rows.sort(key=lambda item: item["case_id"])
    completed = [item for item in model_rows if item["status"] == "completed"]
    graph_metrics = _set_metrics(
        ({tuple(item) for item in row["expected"]}, {tuple(item) for item in row["predicted"]})
        for row in graph_rows
    )
    model_metrics = _set_metrics(
        ({tuple(item) for item in row["expected"]}, {tuple(item) for item in row["predicted"]})
        for row in completed
    )
    model_metrics.update(
        {
            "planned_cases": len(cases),
            "completed_cases": len(completed),
            "citation_valid_cases": sum(item["citation_valid"] for item in completed),
            "citation_entailment_valid_cases": sum(
                item["citation_entailment_valid"] for item in completed
            ),
            "causal_safe_cases": sum(item["causal_safe"] for item in completed),
            "latency_p50_ms": statistics.median(item["elapsed_ms"] for item in completed) if completed else None,
        }
    )
    gate_passed = (
        len(completed) == len(cases)
        and all(
            item["citation_valid"]
            and item["citation_entailment_valid"]
            and item["causal_safe"]
            for item in completed
        )
        and all(item["inference_grade"] == "inferred" for item in model_rows + graph_rows)
    )
    report = {
        "schema_version": "sri.experiment.real-failure-semantic-study.v1",
        "experiment": {
            "name": "evidence-citing-model-vs-ordered-graph-real-run-holdout",
            "evidence_grade": "Experimental",
            "holdout_path": str(arguments.cases.resolve()),
            "holdout_sha256": sha256_path(arguments.cases),
            "model": arguments.model,
            "server_version": arguments.server_version,
            "generation": {"temperature": 0, "enable_thinking": arguments.enable_thinking, "max_tokens": arguments.max_tokens},
            "limitations": [
                "Expected findings are deterministic production candidates, not independent human gold labels.",
                "The real runs come from one local user's database and contain no explicit runtime_failure profile.",
                "The prompt states the known diagnostic relations, so model agreement measures interface reproduction.",
                "Citation entailment is structural and relation-specific; it does not validate natural-language explanations.",
                "All model and graph outputs are Inferred and never modify source evidence.",
            ],
        },
        "ordered_graph_baseline": graph_metrics,
        "evidence_citing_model": model_metrics,
        "graph_rows": graph_rows,
        "model_rows": model_rows,
        "gate": {"name": "completion, citation existence, citation entailment, causal-safety, and inference-layer separation", "passed": gate_passed},
    }
    output = write_report(EXPERIMENT_DIR, "real-failure-semantic-study", report, arguments.output)
    print(json.dumps({"ordered_graph_baseline": graph_metrics, "evidence_citing_model": model_metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
