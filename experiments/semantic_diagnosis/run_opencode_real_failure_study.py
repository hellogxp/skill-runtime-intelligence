#!/usr/bin/env python3
"""Run the real-failure holdout through an installed OpenCode model."""

import argparse
import json
import statistics
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from experiments.common import sha256_path, write_report
from experiments.live_agent.run_cross_agent_cli_trials import (
    _extract_opencode,
    _run_with_process_group,
    _version,
)
from experiments.semantic_diagnosis.run_real_failure_model_study import (
    _entailment_valid,
    _prompt,
    _schema,
    _set_metrics,
    _signature,
)


def _decode_object(text: str) -> Dict[str, Any]:
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    for index, character in enumerate(text):
        if character != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "findings" in value:
            return value
    raise ValueError("no diagnosis JSON object")


def _run_case(case: Dict[str, Any], root: Path, model: str, timeout: float) -> Dict[str, Any]:
    workspace = root / case["case_id"]
    workspace.mkdir()
    request = (
        _prompt(case)
        + "\nThe exact JSON Schema is:\n"
        + json.dumps(_schema(), separators=(",", ":"), sort_keys=True)
    )
    command = ["opencode", "run", "--format", "json", "--auto", "--model", model,
               "--dir", str(workspace), "--title", "SRI independent diagnostic adjudication"]
    started = time.perf_counter()
    try:
        process = _run_with_process_group(command, request, timeout)
        final, session_id, usage = _extract_opencode(process.stdout)
        parsed = _decode_object(final)
    except Exception as error:
        return {"case_id": case["case_id"], "status": "execution_error",
                "error": type(error).__name__, "elapsed_ms": (time.perf_counter() - started) * 1000}
    findings = parsed.get("findings") if isinstance(parsed.get("findings"), list) else []
    valid_ids = {item["evidence_id"] for item in case["evidence"]}
    citation_valid = all(isinstance(item, dict) and isinstance(item.get("citations"), list)
                         and bool(item["citations"]) and set(item["citations"]) <= valid_ids
                         for item in findings)
    expected = {_signature(item) for item in case["expected_findings"]}
    predicted = {_signature(item) for item in findings if isinstance(item, dict)}
    return {"case_id": case["case_id"], "status": "completed" if process.returncode == 0 else "execution_error",
            "expected": sorted(expected), "predicted": sorted(predicted), "predicted_findings": findings,
            "exact": expected == predicted, "citation_valid": citation_valid,
            "citation_entailment_valid": citation_valid and _entailment_valid(findings, case["evidence"]),
            "causal_proven": parsed.get("causal_proven"), "causal_safe": parsed.get("causal_proven") is False,
            "confidence_0_100": parsed.get("confidence_0_100"),
            "elapsed_ms": (time.perf_counter() - started) * 1000, "usage": usage,
            "source_session_present": bool(session_id), "inference_grade": "inferred"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--model", default="opencode/deepseek-v4-flash-free")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--timeout-seconds", type=float, default=180)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    holdout = json.loads(args.cases.read_text(encoding="utf-8"))
    cases = holdout["cases"]
    rows = []
    with tempfile.TemporaryDirectory(prefix="sri-opencode-adjudication-") as directory:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = [executor.submit(_run_case, case, Path(directory), args.model, args.timeout_seconds) for case in cases]
            for future in as_completed(futures):
                rows.append(future.result())
    rows.sort(key=lambda item: item["case_id"])
    completed = [row for row in rows if row["status"] == "completed"]
    metrics = _set_metrics((
        ({tuple(item) for item in row["expected"]}, {tuple(item) for item in row["predicted"]})
        for row in completed
    ))
    metrics.update({"planned_cases": len(cases), "completed_cases": len(completed),
                    "citation_valid_cases": sum(row["citation_valid"] for row in completed),
                    "citation_entailment_valid_cases": sum(row["citation_entailment_valid"] for row in completed),
                    "causal_safe_cases": sum(row["causal_safe"] for row in completed),
                    "latency_p50_ms": statistics.median(row["elapsed_ms"] for row in completed) if completed else None})
    gate = len(completed) == len(cases) and all(
        row["citation_valid"] and row["citation_entailment_valid"] and row["causal_safe"] for row in completed
    )
    report = {"schema_version": "sri.experiment.real-failure-opencode-study.v1",
              "experiment": {"name": "independent-installed-opencode-diagnostic-adjudication",
                 "evidence_grade": "Experimental", "model": args.model, "opencode_version": _version("opencode"),
                 "holdout_sha256": sha256_path(args.cases),
                 "limitations": ["The model is served through an installed Agent CLI, so scaffolding is not isolated.",
                    "Expected labels are deterministic production candidates, not human gold labels.",
                    "Model outputs remain Inferred and disagreement is preserved."]},
              "metrics": metrics, "rows": rows,
              "gate": {"name": "complete independently generated, entailed citations and causal safety", "passed": gate}}
    output = write_report(EXPERIMENT_DIR, "real-failure-opencode-study", report, args.output)
    print(json.dumps({"metrics": metrics, "gate": report["gate"]}, indent=2))
    print(f"Report: {output}")
    return 0 if gate else 1


if __name__ == "__main__":
    raise SystemExit(main())
