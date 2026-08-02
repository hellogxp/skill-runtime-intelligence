#!/usr/bin/env python3
"""Run a rule-label-blinded annotation protocol over deidentified real traces."""

import argparse
import hashlib
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
from experiments.live_agent.run_cross_agent_cli_trials import (
    _extract_codex,
    _run_with_process_group,
    _version,
)


STAGES = ("request", "discovery", "activation", "instructions", "resources", "execution", "artifacts", "outcome")
FINDING_CODES = ("lifecycle_evidence_gap", "outcome_unverified", "run_incomplete", "runtime_failure")
UNCERTAINTY_REASONS = ("none", "insufficient_evidence", "unsupported_capability", "ambiguous_relation")
PROTOCOL = (
    "Act as an independent annotator of deidentified Agent Skill runtime evidence. "
    "You are not given any system-produced diagnosis. Annotate only what the supplied records warrant. "
    "Use this stage order: request, discovery, activation, instructions, resources, execution, artifacts, outcome. "
    "Return at most one finding per code. runtime_failure denotes the earliest explicit failed runtime event. "
    "run_incomplete denotes an explicitly incomplete or interrupted run/session and is assigned to outcome. "
    "lifecycle_evidence_gap denotes only the earliest not_observed lifecycle stage before later observed or "
    "failed activity; unsupported stages do not count as gaps. outcome_unverified is assigned to outcome and "
    "requires explicit evidence that verification was expected but not obtained. Unsupported capability is not "
    "failure. Cite exact evidence_id values. Use abstain only when the evidence cannot support a stable annotation; "
    "when abstain is true, findings must be empty. These records cannot prove that a "
    "Skill caused an outcome, so causal_proven must be false. Return only the schema-conforming JSON object."
)


def _schema() -> dict:
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
                        "citations": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                    },
                    "required": ["code", "stage", "citations"],
                    "additionalProperties": False,
                },
            },
            "abstain": {"type": "boolean"},
            "uncertainty_reason": {"type": "string", "enum": list(UNCERTAINTY_REASONS)},
            "causal_proven": {"type": "boolean"},
            "confidence_0_100": {"type": "number", "minimum": 0, "maximum": 100},
        },
        "required": ["findings", "abstain", "uncertainty_reason", "causal_proven", "confidence_0_100"],
        "additionalProperties": False,
    }


def _prompt(case: dict) -> str:
    return PROTOCOL + "\nEvidence:\n" + json.dumps(case["evidence"], sort_keys=True)


def _score(case: dict, parsed: dict, elapsed_ms: float, usage=None) -> dict:
    valid_ids = {item["evidence_id"] for item in case["evidence"]}
    findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
    citation_valid = all(
        isinstance(item, dict)
        and isinstance(item.get("citations"), list)
        and bool(item["citations"])
        and set(item["citations"]) <= valid_ids
        for item in findings
    )
    abstain_consistent = parsed.get("abstain") is False or not findings
    codes = [item.get("code") for item in findings if isinstance(item, dict)]
    protocol_valid = (
        len(codes) == len(set(codes))
        and all(
            item.get("stage") == "outcome"
            for item in findings
            if item.get("code") in {"run_incomplete", "outcome_unverified"}
        )
    )
    return {
        "case_id": case["case_id"],
        "status": "completed",
        "findings": findings,
        "signature": sorted((item["code"], item["stage"]) for item in findings if isinstance(item, dict)),
        "citation_id_valid": citation_valid,
        "abstain": parsed.get("abstain"),
        "abstain_consistent": abstain_consistent,
        "protocol_valid": protocol_valid,
        "uncertainty_reason": parsed.get("uncertainty_reason"),
        "causal_safe": parsed.get("causal_proven") is False,
        "confidence_0_100": parsed.get("confidence_0_100"),
        "elapsed_ms": elapsed_ms,
        "usage": usage or {},
        "inference_grade": "inferred",
    }


def _run_openai(case: dict, arguments) -> dict:
    payload = {
        "model": arguments.model,
        "messages": [
            {"role": "system", "content": "Return only valid JSON."},
            {"role": "user", "content": _prompt(case)},
        ],
        "temperature": 0,
        "max_tokens": 512,
        "chat_template_kwargs": {"enable_thinking": False},
        "response_format": {"type": "json_schema", "json_schema": {"name": "blinded_trace_annotation", "strict": True, "schema": _schema()}},
    }
    request = urllib.request.Request(
        arguments.api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=arguments.timeout_seconds) as response:
            envelope = json.load(response)
        parsed = json.loads(envelope["choices"][0]["message"]["content"])
        return _score(case, parsed, (time.perf_counter() - started) * 1000, envelope.get("usage"))
    except Exception as error:
        return {"case_id": case["case_id"], "status": "execution_error", "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def _run_codex(case: dict, arguments, root: Path) -> dict:
    workspace = root / case["case_id"]
    workspace.mkdir()
    schema_path = workspace / "annotation-schema.json"
    schema_path.write_text(json.dumps(_schema()), encoding="utf-8")
    command = [
        "codex", "exec", "--json", "--ephemeral", "--sandbox", "read-only",
        "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
        "--output-schema", str(schema_path), "--model", arguments.model,
        "-C", str(workspace), "-",
    ]
    started = time.perf_counter()
    try:
        process = _run_with_process_group(command, _prompt(case), arguments.timeout_seconds)
        final, session_id, usage = _extract_codex(process.stdout)
        if process.returncode != 0:
            raise RuntimeError(f"exit_{process.returncode}")
        parsed = json.loads(final)
        row = _score(case, parsed, (time.perf_counter() - started) * 1000, usage)
        row["source_session_present"] = bool(session_id)
        return row
    except Exception as error:
        return {"case_id": case["case_id"], "status": "execution_error", "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--backend", choices=("openai", "codex"), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--server-version", default="unknown")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    holdout = json.loads(arguments.cases.read_text(encoding="utf-8"))
    cases = holdout["cases"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-blinded-annotation-") as directory:
        root = Path(directory)
        with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
            futures = [
                executor.submit(_run_openai, case, arguments)
                if arguments.backend == "openai"
                else executor.submit(_run_codex, case, arguments, root)
                for case in cases
            ]
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda item: item["case_id"])
    completed = [row for row in rows if row["status"] == "completed"]
    gate = len(completed) == len(cases) and all(
        row["citation_id_valid"] and row["abstain_consistent"]
        and row["protocol_valid"] and row["causal_safe"]
        for row in completed
    )
    protocol_digest = hashlib.sha256((PROTOCOL + json.dumps(_schema(), sort_keys=True)).encode()).hexdigest()
    report = {
        "schema_version": "sri.experiment.blinded-real-trace-annotation.v1",
        "experiment": {
            "name": "rule-label-blinded-model-trace-annotation",
            "evidence_grade": "Experimental",
            "backend": arguments.backend,
            "model": arguments.model,
            "runtime_version": _version("codex") if arguments.backend == "codex" else arguments.server_version,
            "holdout_sha256": sha256_path(arguments.cases),
            "annotation_protocol_sha256": protocol_digest,
            "generation": {"temperature": 0, "max_tokens": 512},
            "blinded_to_rule_labels": True,
            "limitations": [
                "Model annotations are independent of the hidden rule outputs but are not human or production ground truth.",
                "The category definitions encode the intended diagnostic ontology.",
                "The selected traces come from one local corpus and may share adapter patterns.",
                "Annotations remain Inferred and never overwrite source or deterministic records.",
            ],
        },
        "summary": {
            "planned_cases": len(cases),
            "completed_cases": len(completed),
            "citation_id_valid_cases": sum(row["citation_id_valid"] for row in completed),
            "causal_safe_cases": sum(row["causal_safe"] for row in completed),
            "protocol_valid_cases": sum(row["protocol_valid"] for row in completed),
            "abstentions": sum(row["abstain"] is True for row in completed),
            "latency_p50_ms": statistics.median(row["elapsed_ms"] for row in completed) if completed else None,
        },
        "rows": rows,
        "gate": {"name": "complete, ID-valid, abstention-consistent, causal-safe blinded annotations", "passed": gate},
    }
    output = write_report(EXPERIMENT_DIR, f"blinded-trace-annotation-{arguments.backend}", report, arguments.output)
    print(json.dumps({"summary": report["summary"], "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
