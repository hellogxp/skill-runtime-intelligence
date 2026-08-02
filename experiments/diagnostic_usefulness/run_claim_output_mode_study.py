#!/usr/bin/env python3
"""Compare structured claim output with free-text post-classification."""

import argparse
import hashlib
import json
import os
import random
import re
import statistics
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from experiments.diagnostic_usefulness.causal_claim_classifier_benchmark import (
    classify_claim_fail_closed,
)
from experiments.diagnostic_usefulness.run_model_study import _extract_opencode
from skill_runtime_intelligence.diagnostics import (
    CAUSAL_CLAIM_KINDS,
    validate_causal_claim,
)


MODES = ("structured", "free_text")


def _prompt(case: Dict[str, Any], mode: str) -> str:
    definitions = (
        "descriptive = reports evidence or uncertainty without asserting a "
        "causal effect; source_attribution = reports that a source asserted "
        "causality without validating it; skill_outcome_effect = asserts a "
        "positive, negative, hedged, or estimated Skill effect on an outcome."
    )
    prefix = (
        "Classify the quoted claim. Use only its wording and the supplied "
        f"causal scope. {definitions}\n"
        f"Causal scope: {case['causal_scope']}\n"
        f"Claim: {json.dumps(case['text'], ensure_ascii=False)}\n"
    )
    if mode == "structured":
        return (
            prefix
            + "Return exactly one JSON object with claim_kind and allowed. "
            "claim_kind must be descriptive, source_attribution, or "
            "skill_outcome_effect; allowed must be a JSON boolean. Do not "
            "include markdown or reasoning."
        )
    return (
        prefix
        + "Explain your classification and permission decision in one short "
        "natural-language sentence. Do not use JSON, code formatting, or the "
        "enum identifiers above."
    )


def _parse_structured(text: str) -> Dict[str, Any]:
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
    claim_kind = parsed.get("claim_kind")
    if claim_kind not in CAUSAL_CLAIM_KINDS:
        raise ValueError(f"invalid claim_kind: {claim_kind!r}")
    if not isinstance(parsed.get("allowed"), bool):
        raise ValueError("allowed was not a boolean")
    return {"claim_kind": claim_kind, "model_allowed": parsed["allowed"]}


def _invoke(
    trial: Dict[str, Any],
    model: str,
    cli_version: str,
    timeout_seconds: float,
) -> Dict[str, Any]:
    prompt = trial.pop("prompt")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="sri-claim-mode-") as directory:
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
                    "SRI claim output mode trial",
                ],
                check=False,
                capture_output=True,
                text=True,
                input=prompt,
                env=environment,
                timeout=timeout_seconds,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return {
                **trial,
                "status": "execution_error",
                "model_id": model,
                "model_cli_version": cli_version,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error": type(error).__name__,
            }
    elapsed_ms = (time.perf_counter() - started) * 1000
    response_text, session_id, usage = _extract_opencode(completed.stdout)
    base = {
        **trial,
        "model_id": model,
        "model_cli_version": cli_version,
        "elapsed_ms": elapsed_ms,
        "session_id_sha256": (
            hashlib.sha256(session_id.encode()).hexdigest()
            if session_id
            else None
        ),
        "usage": usage,
        "response_sha256": hashlib.sha256(
            response_text.encode()
        ).hexdigest(),
    }
    if completed.returncode != 0:
        return {
            **base,
            "status": "execution_error",
            "error": f"opencode_exit_{completed.returncode}",
        }
    if trial["mode"] == "structured":
        try:
            parsed = _parse_structured(response_text)
        except (ValueError, json.JSONDecodeError) as error:
            return {
                **base,
                "status": "parse_error",
                "error": str(error)[:500],
            }
        predicted_kind = parsed["claim_kind"]
        model_allowed = parsed["model_allowed"]
        classifier_basis = "schema-constrained model enum"
    else:
        parsed = classify_claim_fail_closed(response_text)
        predicted_kind = parsed["claim_kind"]
        model_allowed = None
        classifier_basis = parsed["basis"]
    guard = validate_causal_claim(trial["causal_scope"], predicted_kind)
    return {
        **base,
        "status": "completed",
        "predicted_claim_kind": predicted_kind,
        "claim_kind_correct": predicted_kind
        == trial["expected_claim_kind"],
        "predicted_allowed": guard["allowed"],
        "guard_decision_correct": guard["allowed"]
        == trial["expected_allowed"],
        "false_allow": (
            not trial["expected_allowed"] and guard["allowed"]
        ),
        "false_deny": (
            trial["expected_allowed"] and not guard["allowed"]
        ),
        "classifier_basis": classifier_basis,
        "model_allowed": model_allowed,
        "model_allowed_agrees_guard": (
            model_allowed == guard["allowed"]
            if model_allowed is not None
            else None
        ),
        "free_text_response": (
            response_text[:1000] if trial["mode"] == "free_text" else None
        ),
    }


def _metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    result = {}
    for mode in MODES:
        planned = [row for row in rows if row["mode"] == mode]
        completed = [row for row in planned if row["status"] == "completed"]
        result[mode] = {
            "planned": len(planned),
            "completed": len(completed),
            "response_completion_rate": (
                len(completed) / len(planned) if planned else 0.0
            ),
            "claim_kind_correct": sum(
                bool(row["claim_kind_correct"]) for row in completed
            ),
            "claim_kind_intention_to_treat_accuracy": (
                sum(bool(row["claim_kind_correct"]) for row in completed)
                / len(planned)
                if planned
                else 0.0
            ),
            "guard_decision_correct": sum(
                bool(row["guard_decision_correct"]) for row in completed
            ),
            "guard_decision_intention_to_treat_accuracy": (
                sum(bool(row["guard_decision_correct"]) for row in completed)
                / len(planned)
                if planned
                else 0.0
            ),
            "false_allows": sum(
                bool(row["false_allow"]) for row in completed
            ),
            "false_denies": sum(
                bool(row["false_deny"]) for row in completed
            ),
            "unknown_predictions": sum(
                row["predicted_claim_kind"] == "unknown"
                for row in completed
            ),
            "model_guard_disagreements": sum(
                row.get("model_allowed_agrees_guard") is False
                for row in completed
            ),
            "latency_p50_ms": (
                statistics.median(row["elapsed_ms"] for row in completed)
                if completed
                else 0.0
            ),
        }
    return {
        "planned_trials": len(rows),
        "unique_completed_session_count": len(
            {
                row.get("session_id_sha256")
                for row in rows
                if row["status"] == "completed"
                and row.get("session_id_sha256")
            }
        ),
        "by_mode": result,
        "structured_minus_free_text_kind_accuracy": (
            result["structured"]["claim_kind_intention_to_treat_accuracy"]
            - result["free_text"][
                "claim_kind_intention_to_treat_accuracy"
            ]
        ),
        "structured_minus_free_text_guard_accuracy": (
            result["structured"][
                "guard_decision_intention_to_treat_accuracy"
            ]
            - result["free_text"][
                "guard_decision_intention_to_treat_accuracy"
            ]
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cases",
        type=Path,
        default=EXPERIMENT_DIR / "causal_claim_challenge_cases.jsonl",
    )
    parser.add_argument(
        "--model", default="opencode/deepseek-v4-flash-free"
    )
    parser.add_argument("--seed", type=int, default=20260731)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    cases = load_jsonl(arguments.cases)
    cli_version = subprocess.run(
        ["opencode", "--version"],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    ).stdout.strip()
    trials = []
    for case in cases:
        expected_guard = validate_causal_claim(
            case["causal_scope"], case["expected_claim_kind"]
        )
        if expected_guard["allowed"] != case["expected_allowed"]:
            raise ValueError(
                f"{case['case_id']}: expected_allowed conflicts with scope"
            )
        for mode in MODES:
            prompt = _prompt(case, mode)
            trials.append(
                {
                    "case_id": case["case_id"],
                    "mode": mode,
                    "causal_scope": case["causal_scope"],
                    "expected_claim_kind": case["expected_claim_kind"],
                    "expected_allowed": case["expected_allowed"],
                    "prompt_sha256": hashlib.sha256(
                        prompt.encode()
                    ).hexdigest(),
                    "prompt": prompt,
                }
            )
    random.Random(arguments.seed).shuffle(trials)
    rows = []
    with ThreadPoolExecutor(max_workers=arguments.workers) as executor:
        futures = [
            executor.submit(
                _invoke,
                dict(trial),
                arguments.model,
                cli_version,
                arguments.timeout_seconds,
            )
            for trial in trials
        ]
        for future in as_completed(futures):
            rows.append(future.result())
    rows.sort(key=lambda row: (row["case_id"], row["mode"]))
    metrics = _metrics(rows)
    structured = metrics["by_mode"]["structured"]
    report = {
        "schema_version": "sri.experiment.claim-output-mode-study.v1",
        "experiment": {
            "name": "structured-versus-free-text-claim-output",
            "evidence_grade": "experimental",
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "model": arguments.model,
            "model_cli": "opencode",
            "model_cli_version": cli_version,
            "seed": arguments.seed,
            "session_policy": (
                "fresh pure session per trial; stdin prompt; isolated "
                "temporary XDG state"
            ),
            "limitations": [
                "The challenge corpus is small and hand-authored.",
                "The two output modes use different instructions, so the comparison combines representation and prompting effects.",
                "The free-text path uses the frozen fail-closed-v2 pattern classifier.",
                "One model run does not establish a general causal interface effect.",
            ],
        },
        "metrics": metrics,
        "trials": rows,
        "gates": {
            "structured_response_completion": (
                structured["response_completion_rate"] >= 0.9
            ),
            "structured_kind_accuracy": (
                structured["claim_kind_intention_to_treat_accuracy"] >= 0.8
            ),
            "structured_no_false_allow": (
                structured["false_allows"] == 0
            ),
        },
    }
    report["gate"] = {
        "name": "structured-output exploratory readiness",
        "passed": all(report["gates"].values()),
    }
    output = write_report(
        EXPERIMENT_DIR,
        "claim-output-mode-study",
        report,
        arguments.output,
    )
    print(
        json.dumps(
            {
                "metrics": metrics,
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
