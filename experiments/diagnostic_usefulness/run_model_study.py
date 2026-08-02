#!/usr/bin/env python3
"""Run counterbalanced diagnostic-usefulness trials with fresh model sessions."""

import argparse
import hashlib
import json
import os
import re
import statistics
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.prepare_study import (
    _assignments,
    _gold_stage,
    _raw_view,
)
from experiments.runtime_diagnostics.run_benchmark import _materialize_run
from skill_runtime_intelligence.diagnostics import (
    diagnose_skill_run,
    validate_causal_claim,
)


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


def _stimuli(cases: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result = {}
    for case in cases:
        run = _materialize_run(case["run"])
        findings = diagnose_skill_run(run)
        result[case["case_id"]] = {
            "case_id": case["case_id"],
            "description": case["description"],
            "gold_stage": _gold_stage(case),
            "raw": {
                "view": "redacted source-like event list",
                "lines": _raw_view(run),
            },
            "panorama": {
                "view": "evidence-graded Skill Run Panorama",
                "findings": [
                    {
                        key: finding[key]
                        for key in (
                            "title",
                            "summary",
                            "stage",
                            "severity",
                            "evidence_grade",
                            "causal_scope",
                            "basis",
                            "missing_signals",
                            "recommended_actions",
                        )
                    }
                    for finding in findings
                ],
            },
        }
    return result


def _prompt(stimulus: Dict[str, Any], condition: str) -> str:
    evidence = stimulus[condition]
    return (
        "You are evaluating a Skill runtime diagnostic view. Use only the "
        "evidence below. Do not use tools, files, external knowledge, or hidden "
        "assumptions.\n\n"
        "Task:\n"
        "1. Select the earliest lifecycle stage that failed or lacks expected "
        "evidence before later activity.\n"
        "2. State whether this evidence proves that the Skill caused the final "
        "outcome. Absence of evidence is not proof that an action did not occur.\n"
        "3. Give confidence from 0 to 100.\n\n"
        f"Allowed stages: {', '.join(STAGES)}.\n"
        "Return exactly one JSON object with keys first_boundary, "
        "causal_proven, confidence_0_100, and evidence_reference. "
        "causal_proven must be a JSON boolean. Do not include reasoning or "
        "markdown.\n\n"
        f"Case description: {stimulus['description']}\n"
        f"Condition: {condition}\n"
        "Evidence:\n"
        + json.dumps(evidence, ensure_ascii=False, sort_keys=True)
    )


def _parse_json_object(text: str) -> Dict[str, Any]:
    candidate = text.strip()
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", candidate, re.DOTALL)
        if not match:
            raise ValueError("response did not contain a JSON object")
        parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("response JSON was not an object")
    boundary = str(parsed.get("first_boundary", "")).lower()
    if boundary not in STAGES:
        raise ValueError(f"invalid first_boundary: {boundary!r}")
    if not isinstance(parsed.get("causal_proven"), bool):
        raise ValueError("causal_proven was not a boolean")
    confidence = parsed.get("confidence_0_100")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        raise ValueError("confidence_0_100 was not numeric")
    if not 0 <= float(confidence) <= 100:
        raise ValueError("confidence_0_100 was outside 0..100")
    return {
        "first_boundary": boundary,
        "causal_proven": parsed["causal_proven"],
        "confidence_0_100": float(confidence),
        "evidence_reference": str(parsed.get("evidence_reference", ""))[:500],
    }


def _extract_opencode(stdout: str) -> tuple[str, Optional[str], Dict[str, Any]]:
    texts: List[str] = []
    session_id = None
    usage: Dict[str, Any] = {}
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        session_id = session_id or event.get("sessionID")
        part = event.get("part") or {}
        if event.get("type") == "text" and isinstance(part.get("text"), str):
            texts.append(part["text"])
        if event.get("type") == "step_finish":
            usage = part.get("tokens") or {}
            if part.get("cost") is not None:
                usage["reported_cost"] = part["cost"]
    return "".join(texts), session_id, usage


def _run_opencode_trial(
    trial: Dict[str, Any],
    model: str,
    cli_version: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    prompt = trial.pop("prompt")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="sri-model-trial-") as directory:
        environment = os.environ.copy()
        environment.update(
            {
                "XDG_CACHE_HOME": str(Path(directory) / "cache"),
                "XDG_CONFIG_HOME": str(Path(directory) / "config"),
                "XDG_DATA_HOME": str(Path(directory) / "data"),
                "XDG_STATE_HOME": str(Path(directory) / "state"),
                "OPENCODE_CONFIG_DIR": str(
                    Path(directory) / "opencode-config"
                ),
            }
        )
        try:
            completed = subprocess.run(
                [
                    "opencode",
                    "run",
                    "--pure",
                    "--format",
                    "json",
                    "-m",
                    model,
                    "--dir",
                    directory,
                    "--title",
                    "SRI diagnostic usefulness trial",
                ],
                check=False,
                capture_output=True,
                text=True,
                input=prompt,
                env=environment,
                timeout=timeout_seconds,
            )
            elapsed_ms = (time.perf_counter() - started) * 1000
        except (OSError, subprocess.TimeoutExpired) as error:
            return {
                **trial,
                "status": "execution_error",
                "model_provider": model.split("/", 1)[0],
                "model_id": model,
                "model_cli": "opencode",
                "model_cli_version": cli_version,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error": type(error).__name__,
            }
    response_text, session_id, usage = _extract_opencode(completed.stdout)
    base = {
        **trial,
        "model_provider": model.split("/", 1)[0],
        "model_id": model,
        "model_cli": "opencode",
        "model_cli_version": cli_version,
        "elapsed_ms": elapsed_ms,
        "session_id_sha256": (
            hashlib.sha256(session_id.encode()).hexdigest()
            if session_id
            else None
        ),
        "usage": usage,
    }
    if completed.returncode != 0:
        return {
            **base,
            "status": "execution_error",
            "error": f"opencode_exit_{completed.returncode}",
        }
    try:
        response = _parse_json_object(response_text)
    except (ValueError, json.JSONDecodeError) as error:
        return {
            **base,
            "status": "parse_error",
            "error": str(error)[:500],
            "response_sha256": hashlib.sha256(
                response_text.encode()
            ).hexdigest(),
        }
    correct = response["first_boundary"] == trial["gold_stage"]
    claim_kind = (
        "skill_outcome_effect"
        if response["causal_proven"]
        else "descriptive"
    )
    causal_guard = validate_causal_claim("none", claim_kind)
    return {
        **base,
        "status": "completed",
        "first_boundary_answer": response["first_boundary"],
        "correct": correct,
        "confidence_0_100": response["confidence_0_100"],
        "causal_proven": response["causal_proven"],
        "causal_guard": causal_guard,
        "unsupported_causal_claim": not causal_guard["allowed"],
        "evidence_reference": response["evidence_reference"],
    }


def _run_openai_compatible_trial(
    trial: Dict[str, Any],
    model: str,
    api_base: str,
    api_key: Optional[str],
    server_version: str,
    timeout_seconds: float,
    max_tokens: int,
    temperature: float,
    enable_thinking: bool,
) -> Dict[str, Any]:
    prompt = trial.pop("prompt")
    schema = {
        "type": "object",
        "properties": {
            "first_boundary": {"type": "string", "enum": list(STAGES)},
            "causal_proven": {"type": "boolean"},
            "confidence_0_100": {
                "type": "number",
                "minimum": 0,
                "maximum": 100,
            },
            "evidence_reference": {"type": "string"},
        },
        "required": [
            "first_boundary",
            "causal_proven",
            "confidence_0_100",
            "evidence_reference",
        ],
        "additionalProperties": False,
    }
    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Follow the user instruction and return only one JSON "
                    "object matching the supplied schema."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "chat_template_kwargs": {"enable_thinking": enable_thinking},
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "sri_diagnostic_usefulness",
                "strict": True,
                "schema": schema,
            },
        },
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    request = urllib.request.Request(
        api_base.rstrip("/") + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout_seconds,
        ) as response_stream:
            response_payload = json.load(response_stream)
        elapsed_ms = (time.perf_counter() - started) * 1000
        response_text = response_payload["choices"][0]["message"]["content"]
        response_id = str(response_payload.get("id") or "")
        usage = dict(response_payload.get("usage") or {})
    except (
        OSError,
        KeyError,
        IndexError,
        TypeError,
        ValueError,
        urllib.error.HTTPError,
        urllib.error.URLError,
    ) as error:
        return {
            **trial,
            "status": "execution_error",
            "model_provider": "openai-compatible",
            "model_id": model,
            "model_cli": "openai-compatible-http",
            "model_cli_version": server_version,
            "elapsed_ms": (time.perf_counter() - started) * 1000,
            "error": type(error).__name__,
        }
    base = {
        **trial,
        "model_provider": "openai-compatible",
        "model_id": model,
        "model_cli": "openai-compatible-http",
        "model_cli_version": server_version,
        "elapsed_ms": elapsed_ms,
        "session_id_sha256": (
            hashlib.sha256(response_id.encode()).hexdigest()
            if response_id
            else None
        ),
        "usage": usage,
    }
    try:
        response = _parse_json_object(response_text)
    except (ValueError, json.JSONDecodeError) as error:
        return {
            **base,
            "status": "parse_error",
            "error": str(error)[:500],
            "response_sha256": hashlib.sha256(
                response_text.encode()
            ).hexdigest(),
        }
    correct = response["first_boundary"] == trial["gold_stage"]
    claim_kind = (
        "skill_outcome_effect"
        if response["causal_proven"]
        else "descriptive"
    )
    causal_guard = validate_causal_claim("none", claim_kind)
    return {
        **base,
        "status": "completed",
        "first_boundary_answer": response["first_boundary"],
        "correct": correct,
        "confidence_0_100": response["confidence_0_100"],
        "causal_proven": response["causal_proven"],
        "causal_guard": causal_guard,
        "unsupported_causal_claim": not causal_guard["allowed"],
        "evidence_reference": response["evidence_reference"],
    }


def _rate(rows: List[Dict[str, Any]], key: str) -> float:
    return sum(bool(row[key]) for row in rows) / len(rows) if rows else 0.0


def _metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    completed = [row for row in rows if row["status"] == "completed"]
    by_condition = {}
    for condition in ("raw", "panorama"):
        planned_condition_rows = [
            row for row in rows if row["condition"] == condition
        ]
        condition_rows = [
            row for row in completed if row["condition"] == condition
        ]
        brier = [
            (
                row["confidence_0_100"] / 100
                - (1.0 if row["correct"] else 0.0)
            )
            ** 2
            for row in condition_rows
        ]
        by_condition[condition] = {
            "planned": len(planned_condition_rows),
            "completed": len(condition_rows),
            "correct": sum(bool(row["correct"]) for row in condition_rows),
            "complete_case_accuracy": _rate(condition_rows, "correct"),
            "intention_to_treat_accuracy": (
                sum(bool(row["correct"]) for row in condition_rows)
                / len(planned_condition_rows)
                if planned_condition_rows
                else 0.0
            ),
            "unsupported_causal_claim_rate": _rate(
                condition_rows, "unsupported_causal_claim"
            ),
            "mean_confidence_0_100": (
                statistics.fmean(
                    row["confidence_0_100"] for row in condition_rows
                )
                if condition_rows
                else 0.0
            ),
            "brier_score": statistics.fmean(brier) if brier else 0.0,
            "latency_p50_ms": (
                statistics.median(row["elapsed_ms"] for row in condition_rows)
                if condition_rows
                else 0.0
            ),
        }
    case_pairs = []
    for case_id in sorted({row["case_id"] for row in completed}):
        raw = [
            row for row in completed
            if row["case_id"] == case_id and row["condition"] == "raw"
        ]
        panorama = [
            row for row in completed
            if row["case_id"] == case_id and row["condition"] == "panorama"
        ]
        if raw and panorama:
            case_pairs.append(
                {
                    "case_id": case_id,
                    "raw_accuracy": _rate(raw, "correct"),
                    "panorama_accuracy": _rate(panorama, "correct"),
                }
            )
    panorama_wins = sum(
        pair["panorama_accuracy"] > pair["raw_accuracy"]
        for pair in case_pairs
    )
    raw_wins = sum(
        pair["raw_accuracy"] > pair["panorama_accuracy"]
        for pair in case_pairs
    )
    return {
        "planned_trials": len(rows),
        "completed_trials": len(completed),
        "response_completion_rate": len(completed) / len(rows) if rows else 0.0,
        "unique_session_count": len(
            {
                row["session_id_sha256"]
                for row in completed
                if row.get("session_id_sha256")
            }
        ),
        "overall_accuracy": _rate(completed, "correct"),
        "overall_unsupported_causal_claim_rate": _rate(
            completed, "unsupported_causal_claim"
        ),
        "by_condition": by_condition,
        "panorama_minus_raw_complete_case_accuracy": (
            by_condition["panorama"]["complete_case_accuracy"]
            - by_condition["raw"]["complete_case_accuracy"]
        ),
        "panorama_minus_raw_intention_to_treat_accuracy": (
            by_condition["panorama"]["intention_to_treat_accuracy"]
            - by_condition["raw"]["intention_to_treat_accuracy"]
        ),
        "matched_case_count": len(case_pairs),
        "matched_case_direction": {
            "panorama_wins": panorama_wins,
            "raw_wins": raw_wins,
            "ties": len(case_pairs) - panorama_wins - raw_wins,
        },
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
    parser.add_argument("--model-samples", type=int, default=2)
    parser.add_argument(
        "--model", default="opencode/deepseek-v4-flash-free"
    )
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument(
        "--api-base",
        help=(
            "OpenAI-compatible /v1 endpoint. When set, bypass OpenCode and "
            "run one independent HTTP request per trial."
        ),
    )
    parser.add_argument(
        "--api-key-env",
        help="Optional environment variable containing the API key.",
    )
    parser.add_argument("--api-server-version", default="unknown")
    parser.add_argument("--max-tokens", type=int, default=256)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--enable-thinking", action="store_true")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    if arguments.model_samples < 1:
        parser.error("--model-samples must be at least 1")
    cases = [
        case for case in load_jsonl(arguments.cases) if case["expected_findings"]
    ]
    stimuli = _stimuli(cases)
    assignments = _assignments(
        list(stimuli), arguments.model_samples, arguments.seed
    )
    if arguments.api_base:
        cli_version = arguments.api_server_version
        api_key = (
            os.environ.get(arguments.api_key_env)
            if arguments.api_key_env
            else None
        )
    else:
        cli_version = subprocess.run(
            ["opencode", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
        api_key = None
    trials = []
    for assignment in assignments:
        for order_index, item in enumerate(assignment["case_order"]):
            stimulus = stimuli[item["case_id"]]
            prompt = _prompt(stimulus, item["condition"])
            trials.append(
                {
                    "model_sample_slot": assignment["model_sample_slot"],
                    "order_index": order_index,
                    "case_id": item["case_id"],
                    "condition": item["condition"],
                    "gold_stage": stimulus["gold_stage"],
                    "prompt_sha256": hashlib.sha256(
                        prompt.encode()
                    ).hexdigest(),
                    "prompt": prompt,
                }
            )
    rows = []
    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        if arguments.api_base:
            futures = [
                executor.submit(
                    _run_openai_compatible_trial,
                    dict(trial),
                    arguments.model,
                    arguments.api_base,
                    api_key,
                    cli_version,
                    arguments.timeout_seconds,
                    arguments.max_tokens,
                    arguments.temperature,
                    arguments.enable_thinking,
                )
                for trial in trials
            ]
        else:
            futures = [
                executor.submit(
                    _run_opencode_trial,
                    dict(trial),
                    arguments.model,
                    cli_version,
                    arguments.timeout_seconds,
                )
                for trial in trials
            ]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(
        key=lambda row: (
            row["model_sample_slot"],
            row["order_index"],
            row["case_id"],
        )
    )
    metrics = _metrics(rows)
    report = {
        "schema_version": "sri.experiment.model-agent-usefulness-result.v1",
        "experiment": {
            "name": "counterbalanced-model-agent-diagnostic-usefulness",
            "evidence_grade": "experimental",
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "seed": arguments.seed,
            "model": arguments.model,
            "model_cli": (
                "openai-compatible-http" if arguments.api_base else "opencode"
            ),
            "model_cli_version": cli_version,
            "session_policy": (
                "one independent schema-constrained HTTP request per trial; "
                "no conversation reuse"
                if arguments.api_base
                else "fresh pure session per trial; prompt via stdin; isolated "
                "temporary XDG state deleted after response"
            ),
            "generation": {
                "temperature": arguments.temperature,
                "max_tokens": arguments.max_tokens,
                "enable_thinking": arguments.enable_thinking,
                "structured_output": bool(arguments.api_base),
            },
            "limitations": [
                "These are model-agent responses, not human participants.",
                "Repeated sessions from one model are stochastic samples, not independent model families.",
                "The synthetic cases were built from the deterministic diagnostic corpus.",
                "Latency is specific to this model/provider/CLI environment.",
                "A condition difference from this pilot is exploratory and is not a general causal product claim.",
            ],
        },
        "metrics": metrics,
        "trials": rows,
        "gate": {
            "name": "model-agent pilot integrity",
            "passed": (
                metrics["completed_trials"] == metrics["planned_trials"]
                and metrics["unique_session_count"]
                == metrics["completed_trials"]
                and metrics["overall_unsupported_causal_claim_rate"] == 0.0
            ),
        },
    }
    output = write_report(
        EXPERIMENT_DIR,
        "model-agent-diagnostic-usefulness",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {"metrics": metrics, "gate_passed": report["gate"]["passed"]},
            indent=2,
        )
    )
    print(f"Report: {output}")
    return 0 if report["gate"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
