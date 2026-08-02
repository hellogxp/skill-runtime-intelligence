#!/usr/bin/env python3
"""Evaluate rule-external anomaly hypotheses with citations."""

import argparse
import json
import statistics
import sys
import tempfile
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.live_agent.run_cross_agent_cli_trials import _extract_opencode, _run_with_process_group, _version
from experiments.semantic_diagnosis.run_opencode_real_failure_study import _decode_object


def _schema():
    return {"type": "object", "properties": {
        "anomaly_present": {"type": "boolean"}, "anomaly_label": {"type": "string"},
        "citations": {"type": "array", "items": {"type": "string"}},
        "causal_proven": {"type": "boolean"}, "confidence_0_100": {"type": "number", "minimum": 0, "maximum": 100}},
        "required": ["anomaly_present", "anomaly_label", "citations", "causal_proven", "confidence_0_100"],
        "additionalProperties": False}


def _prompt(case):
    return ("Inspect this de-identified runtime evidence fragment for an internal consistency anomaly beyond the standard "
            "lifecycle-gap, runtime-failure, incomplete-run, and unverified-outcome rules. Do not assume missing events did not occur. "
            "If an anomaly is present, give a short descriptive label and cite the exact evidence_id rows that jointly establish it. "
            "If none is present, set anomaly_present false and citations empty. Evidence does not establish Skill causal effectiveness; "
            "causal_proven must be false. Return only JSON matching this schema:\n" + json.dumps(_schema(), sort_keys=True) +
            "\nEvidence:\n" + json.dumps(case["evidence"], sort_keys=True))


def _score(case, parsed, elapsed, usage=None):
    citations = parsed.get("citations") if isinstance(parsed.get("citations"), list) else []
    valid = set(citations) <= {item["evidence_id"] for item in case["evidence"]}
    support = set(case["expected_support"])
    supported = (not case["anomaly_present"] and citations == []) or (case["anomaly_present"] and support <= set(citations))
    predicted = parsed.get("anomaly_present") is True
    return {"case_id": case["case_id"], "family": case["family"], "status": "completed",
            "expected_anomaly": case["anomaly_present"], "predicted_anomaly": predicted,
            "detection_correct": predicted == case["anomaly_present"], "citations": citations,
            "citation_id_valid": valid, "support_relation_valid": valid and supported,
            "anomaly_label": parsed.get("anomaly_label"), "causal_safe": parsed.get("causal_proven") is False,
            "confidence_0_100": parsed.get("confidence_0_100"), "elapsed_ms": elapsed, "usage": usage or {}}


def _http(case, api_base, model, timeout):
    payload = {"model": model, "messages": [{"role": "system", "content": "Return only valid JSON."},
              {"role": "user", "content": _prompt(case)}], "temperature": 0, "max_tokens": 384,
              "chat_template_kwargs": {"enable_thinking": False},
              "response_format": {"type": "json_schema", "json_schema": {"name": "novel_pattern", "strict": True, "schema": _schema()}}}
    request = urllib.request.Request(api_base.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            envelope = json.load(response)
        parsed = json.loads(envelope["choices"][0]["message"]["content"])
        return _score(case, parsed, (time.perf_counter() - started) * 1000, envelope.get("usage"))
    except Exception as error:
        return {"case_id": case["case_id"], "family": case["family"], "status": "execution_error", "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def _opencode(case, root, model, timeout):
    workspace = root / case["case_id"]
    workspace.mkdir()
    command = ["opencode", "run", "--format", "json", "--auto", "--model", model, "--dir", str(workspace), "--title", "SRI novel-pattern study"]
    started = time.perf_counter()
    try:
        process = _run_with_process_group(command, _prompt(case), timeout)
        final, _, usage = _extract_opencode(process.stdout)
        if process.returncode != 0:
            raise RuntimeError(f"exit_{process.returncode}")
        return _score(case, _decode_object(final), (time.perf_counter() - started) * 1000, usage)
    except Exception as error:
        return {"case_id": case["case_id"], "family": case["family"], "status": "execution_error", "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--backend", choices=("openai", "opencode"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-novel-pattern-") as directory:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_http, case, args.api_base, args.model, args.timeout_seconds) if args.backend == "openai"
                       else executor.submit(_opencode, case, Path(directory), args.model, args.timeout_seconds) for case in cases]
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda row: row["case_id"])
    completed = [row for row in rows if row["status"] == "completed"]
    tp = sum(row["expected_anomaly"] and row["predicted_anomaly"] for row in completed)
    fp = sum(not row["expected_anomaly"] and row["predicted_anomaly"] for row in completed)
    fn = sum(row["expected_anomaly"] and not row["predicted_anomaly"] for row in completed)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    metrics = {"planned_cases": len(cases), "completed_cases": len(completed),
               "detection_correct": sum(row["detection_correct"] for row in completed),
               "precision": precision, "recall": recall,
               "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0,
               "citation_id_valid": sum(row["citation_id_valid"] for row in completed),
               "support_relation_valid": sum(row["support_relation_valid"] for row in completed),
               "causal_safe": sum(row["causal_safe"] for row in completed),
               "latency_p50_ms": statistics.median(row["elapsed_ms"] for row in completed) if completed else None,
               "rule_baseline_detected": 0}
    gate = len(completed) == len(cases) and all(row["citation_id_valid"] and row["causal_safe"] for row in completed)
    report = {"schema_version": "sri.experiment.novel-pattern-study.v1",
              "experiment": {"name": "rule-external-paired-anomaly-discovery", "evidence_grade": "Experimental",
                 "backend": args.backend, "model": args.model, "runtime_version": _version("opencode") if args.backend == "opencode" else "openai-compatible",
                 "holdout_sha256": sha256_path(args.cases),
                 "limitations": ["Controlled synthetic invariants are hypothesis tests, not real incident prevalence.",
                    "The rule baseline is intentionally zero because these families are outside the production rule set.",
                    "Support validation checks preregistered evidence pairs, not natural-language semantic quality."]},
              "metrics": metrics, "rows": rows,
              "gate": {"name": "complete, ID-valid, causal-safe hypothesis generation", "passed": gate}}
    output = write_report(EXPERIMENT_DIR, f"novel-pattern-{args.backend}", report, args.output)
    print(json.dumps({"metrics": metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
