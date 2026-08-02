#!/usr/bin/env python3
"""Compare Raw, Panorama, graph-only, and graph-plus-model diagnosis."""

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


STAGES = ("none", "instructions", "resources", "execution", "artifacts", "outcome")
STATUSES = ("verified_success", "observed_failure", "outcome_unverified", "verifier_conflict")
VIEWS = ("raw", "raw_semantic", "panorama", "graph_plus_model")


RAW_LEGEND = (
    "Raw records use phase ordinal 1..5 corresponding to instructions, resources, "
    "execution, artifacts, outcome; native status codes are 0=observed, 1=failed, "
    "2=not observed, 3=not verified. "
)


def _schema():
    return {"type": "object", "properties": {
        "boundary": {"type": "string", "enum": list(STAGES)},
        "diagnosis_status": {"type": "string", "enum": list(STATUSES)},
        "citations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "causal_proven": {"type": "boolean"}, "confidence_0_100": {"type": "number", "minimum": 0, "maximum": 100}},
        "required": ["boundary", "diagnosis_status", "citations", "causal_proven", "confidence_0_100"],
        "additionalProperties": False}


def _raw_semantic_evidence(case):
    """Retain native records while adding field-level aliases from Panorama."""
    stage_by_ordinal = dict(enumerate(STAGES[1:], 1))
    status_by_code = {0: "observed", 1: "failed", 2: "not_observed", 3: "not_verified"}
    records = []
    for item in case["raw_evidence"]:
        record = dict(item)
        native_type = item.get("native_type")
        if native_type == "probe.step":
            record.update({
                "semantic_kind": "lifecycle_stage",
                "semantic_stage": stage_by_ordinal.get(item.get("ordinal")),
                "semantic_status": status_by_code.get(item.get("native_status_code")),
                "evidence_grade": "experimental",
            })
        elif native_type == "agent.result":
            record.update({
                "semantic_kind": "reported_outcome",
                "semantic_status": item.get("value"),
                "evidence_grade": "experimental",
            })
        elif native_type == "external.check":
            record.update({
                "semantic_kind": "external_verifier",
                "semantic_status": item.get("value"),
                "evidence_grade": "experimental",
            })
        else:
            record["semantic_kind"] = "auxiliary_runtime_context"
        records.append(record)
    return records


def _evidence(case, view):
    if view == "raw":
        return case["raw_evidence"]
    if view == "raw_semantic":
        return _raw_semantic_evidence(case)
    if view == "panorama":
        return case["panorama_evidence"]
    return case["panorama_evidence"] + [{"evidence_id": "G01", "kind": "deterministic_graph_candidate", **case["graph_candidate"]}]


def _prompt(case, view):
    context = RAW_LEGEND if view == "raw" else ""
    return ("Diagnose the earliest observable boundary of this controlled Skill run. " + context +
            "A reported success plus verifier not_configured is outcome_unverified; reported success plus verifier failed is verifier_conflict. "
            "All evidence is Experimental and cannot prove causal Skill effectiveness, so causal_proven must be false. "
            "Cite exact evidence_id values that establish the status and boundary. Return only JSON matching this schema:\n" +
            json.dumps(_schema(), sort_keys=True) + "\nEvidence:\n" + json.dumps(_evidence(case, view), sort_keys=True))


def _citation_entails(case, view, parsed):
    evidence = {item["evidence_id"]: item for item in _evidence(case, view)}
    citations = parsed.get("citations")
    if not isinstance(citations, list) or not citations or not set(citations) <= set(evidence):
        return False
    cited = [evidence[item] for item in citations]
    boundary, status = parsed.get("boundary"), parsed.get("diagnosis_status")
    if any(item.get("kind") == "deterministic_graph_candidate" and
           item.get("boundary") == boundary and item.get("diagnosis_status") == status for item in cited):
        return True
    if view in {"raw", "raw_semantic"}:
        phase = next((item for item in cited if item.get("native_type") == "probe.step" and
                      item.get("ordinal") == STAGES.index(boundary) and item.get("native_status_code") in {1, 3}), None) if boundary != "none" else None
        reported = next((item for item in cited if item.get("native_type") == "agent.result"), None)
        verifier = next((item for item in cited if item.get("native_type") == "external.check"), None)
    else:
        phase = next((item for item in cited if item.get("kind") == "lifecycle_stage" and
                      item.get("stage") == boundary and item.get("status") in {"failed", "not_verified"}), None)
        reported = next((item for item in cited if item.get("kind") == "reported_outcome"), None)
        verifier = next((item for item in cited if item.get("kind") == "external_verifier"), None)
    if status == "observed_failure":
        return bool(phase is not None and boundary != "outcome")
    if status == "outcome_unverified":
        return bool(phase is not None and reported and reported.get("value", reported.get("status")) == "success" and verifier and verifier.get("value", verifier.get("status")) == "not_configured")
    if status == "verifier_conflict":
        return bool(phase is not None and reported and reported.get("value", reported.get("status")) == "success" and verifier and verifier.get("value", verifier.get("status")) == "failed")
    if status == "verified_success":
        return bool(boundary == "none" and reported and reported.get("value", reported.get("status")) == "success" and verifier and verifier.get("value", verifier.get("status")) == "passed")
    return False


def _score(case, view, parsed, elapsed, usage=None):
    predicted = {"boundary": parsed.get("boundary"), "diagnosis_status": parsed.get("diagnosis_status")}
    valid_ids = {item["evidence_id"] for item in _evidence(case, view)}
    citations = parsed.get("citations") if isinstance(parsed.get("citations"), list) else []
    return {"case_id": case["case_id"], "agent": case["agent"], "repo_key": case["repo_key"],
            "fault_mode": case["fault_mode"], "view": view, "status": "completed", "gold": case["gold"],
            "predicted": predicted, "exact": predicted == case["gold"],
            "boundary_exact": predicted["boundary"] == case["gold"]["boundary"],
            "status_exact": predicted["diagnosis_status"] == case["gold"]["diagnosis_status"],
            "citation_id_valid": bool(citations) and set(citations) <= valid_ids,
            "citation_entailment_valid": _citation_entails(case, view, parsed),
            "causal_safe": parsed.get("causal_proven") is False,
            "confidence_0_100": parsed.get("confidence_0_100"), "elapsed_ms": elapsed, "usage": usage or {}}


def _http(case, view, api_base, model, timeout):
    payload = {"model": model, "messages": [{"role": "system", "content": "Return only valid JSON."},
              {"role": "user", "content": _prompt(case, view)}], "temperature": 0, "max_tokens": 384,
              "chat_template_kwargs": {"enable_thinking": False},
              "response_format": {"type": "json_schema", "json_schema": {"name": "multirepo_diagnosis", "strict": True, "schema": _schema()}}}
    request = urllib.request.Request(api_base.rstrip("/") + "/chat/completions", data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            envelope = json.load(response)
        return _score(case, view, json.loads(envelope["choices"][0]["message"]["content"]),
                      (time.perf_counter() - started) * 1000, envelope.get("usage"))
    except Exception as error:
        return {"case_id": case["case_id"], "agent": case["agent"], "repo_key": case["repo_key"],
                "fault_mode": case["fault_mode"], "view": view, "status": "execution_error",
                "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def _opencode(case, view, root, model, timeout):
    workspace = root / f"{case['case_id']}-{view}"
    workspace.mkdir()
    command = ["opencode", "run", "--format", "json", "--auto", "--model", model,
               "--dir", str(workspace), "--title", "SRI multirepo diagnostic utility"]
    started = time.perf_counter()
    try:
        process = _run_with_process_group(command, _prompt(case, view), timeout)
        final, _, usage = _extract_opencode(process.stdout)
        if process.returncode != 0:
            raise RuntimeError(f"exit_{process.returncode}")
        return _score(case, view, _decode_object(final), (time.perf_counter() - started) * 1000, usage)
    except Exception as error:
        return {"case_id": case["case_id"], "agent": case["agent"], "repo_key": case["repo_key"],
                "fault_mode": case["fault_mode"], "view": view, "status": "execution_error",
                "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def _summary(rows):
    result = {}
    for view in VIEWS:
        selected = [row for row in rows if row["view"] == view]
        completed = [row for row in selected if row["status"] == "completed"]
        result[view] = {"planned": len(selected), "completed": len(completed),
                        "exact": sum(row["exact"] for row in completed),
                        "exact_rate": sum(row["exact"] for row in completed) / len(completed) if completed else 0.0,
                        "boundary_exact": sum(row["boundary_exact"] for row in completed),
                        "status_exact": sum(row["status_exact"] for row in completed),
                        "citation_id_valid": sum(row["citation_id_valid"] for row in completed),
                        "citation_entailment_valid": sum(row["citation_entailment_valid"] for row in completed),
                        "causal_safe": sum(row["causal_safe"] for row in completed),
                        "latency_p50_ms": statistics.median(row["elapsed_ms"] for row in completed) if completed else None,
                        "input_tokens_total": sum((row.get("usage") or {}).get("input_tokens", (row.get("usage") or {}).get("input", 0)) or 0 for row in completed)}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--backend", choices=("openai", "opencode"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--views", default=",".join(VIEWS))
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    views = tuple(item for item in args.views.split(",") if item)
    if not views or not set(views) <= set(VIEWS):
        parser.error(
            "views must be a non-empty subset of "
            "raw,raw_semantic,panorama,graph_plus_model"
        )
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    graph_rows = [{"case_id": case["case_id"], "gold": case["gold"], "predicted": {key: case["graph_candidate"][key] for key in ("boundary", "diagnosis_status")},
                   "exact": all(case["graph_candidate"][key] == case["gold"][key] for key in ("boundary", "diagnosis_status"))} for case in cases]
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-multirepo-diagnosis-") as directory:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_http, case, view, args.api_base, args.model, args.timeout_seconds)
                       if args.backend == "openai" else executor.submit(_opencode, case, view, Path(directory), args.model, args.timeout_seconds)
                       for case in cases for view in views]
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda row: (row["case_id"], row["view"]))
    summary = _summary(rows)
    planned = len(cases) * len(views)
    completed = sum(row["status"] == "completed" for row in rows)
    graph_exact = sum(row["exact"] for row in graph_rows)
    gate = completed == planned and all(row.get("citation_id_valid") and row.get("causal_safe") for row in rows if row["status"] == "completed")
    report = {"schema_version": "sri.experiment.multirepo-diagnostic-utility.v1",
              "experiment": {"name": "raw-semantics-matched-panorama-graph-plus-model-multirepo-diagnosis", "evidence_grade": "Experimental",
                 "backend": args.backend, "model": args.model, "runtime_version": _version("opencode") if args.backend == "opencode" else "openai-compatible",
                 "holdout_sha256": sha256_path(args.cases), "views": list(views),
                 "limitations": ["Gold is programmatic controlled-fault truth, not natural production-incident annotation.",
                    "Raw and Panorama are two representations of the same executed oracle trace.",
                    "Raw-semantic preserves every raw field and auxiliary record while adding inline lifecycle, record-kind, status, and evidence-grade aliases corresponding to Panorama; it contrasts a semantically explicit noisy flat view with the compact normalized view.",
                    "Graph-plus-model exposes a correct deterministic candidate; it tests interface preservation, not independent discovery.",
                    "All model conclusions remain Inferred even when exact."]},
              "graph_only": {"planned": len(graph_rows), "exact": graph_exact, "exact_rate": graph_exact / len(graph_rows) if graph_rows else 0.0},
              "model_summary": summary, "graph_rows": graph_rows, "rows": rows,
              "gate": {"name": "all requested calls complete with ID-valid citations and causal safety", "passed": gate}}
    output = write_report(EXPERIMENT_DIR, f"multirepo-diagnostic-{args.backend}", report, args.output)
    print(json.dumps({"graph_only": report["graph_only"], "model_summary": summary, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
