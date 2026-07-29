#!/usr/bin/env python3
"""Run the deterministic SkillRun diagnostics benchmark.

The benchmark imports the production diagnosis function. Cases stay in JSONL
so fault scenarios and labels can evolve without changing evaluator code.
"""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
SOURCE_ROOT = REPOSITORY_ROOT / "src"
sys.path.insert(0, str(SOURCE_ROOT))

from skill_runtime_intelligence.diagnostics import STAGES, diagnose_skill_run


def _git_value(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=REPOSITORY_ROOT,
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return "unavailable"


def _environment() -> Dict[str, Any]:
    git_status = _git_value("status", "--porcelain")
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "hostname": platform.node(),
        "git_commit": _git_value("rev-parse", "HEAD"),
        "git_dirty": git_status not in {"", "unavailable"},
        "pai_dsw_instance_id": os.environ.get("PAI_DSW_INSTANCE_ID"),
        "experiment_root": os.environ.get("SRI_EXPERIMENT_ROOT"),
    }


def _load_cases(path: Path) -> List[Dict[str, Any]]:
    cases = []
    with path.open(encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise ValueError(f"{path}:{line_number}: {error}") from error
    if not cases:
        raise ValueError(f"No cases found in {path}")
    return cases


def _materialize_run(specification: Dict[str, Any]) -> Dict[str, Any]:
    run = dict(specification)
    observed = set(run.pop("observed_stages", []))
    failed = set(run.pop("failed_stages", []))
    unsupported = set(run.pop("unsupported_stages", []))
    stage_summary = []
    for stage in STAGES:
        if stage in unsupported:
            status = "unsupported"
            capability = "unsupported"
        elif stage in failed:
            status = "failed"
            capability = "observed"
        elif stage in observed:
            status = "observed"
            capability = "observed"
        else:
            status = "not_observed"
            capability = "partial"
        stage_summary.append(
            {
                "stage": stage,
                "status": status,
                "capability": capability,
                "event_count": sum(
                    event.get("stage") == stage for event in run.get("events", [])
                ),
            }
        )
    run["stage_summary"] = stage_summary
    return run


def _signature(finding: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        finding.get("code", ""),
        finding.get("stage", ""),
        finding.get("evidence_grade", ""),
    )


def _evaluate(cases: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    results = []
    true_positive = false_positive = false_negative = 0
    exact_matches = 0
    unsupported_causal_claims = []
    for case in cases:
        actual = diagnose_skill_run(_materialize_run(case["run"]))
        expected_signatures = {_signature(item) for item in case["expected_findings"]}
        actual_signatures = {_signature(item) for item in actual}
        matched = expected_signatures & actual_signatures
        missed = expected_signatures - actual_signatures
        unexpected = actual_signatures - expected_signatures
        true_positive += len(matched)
        false_positive += len(unexpected)
        false_negative += len(missed)
        exact_match = not missed and not unexpected
        exact_matches += int(exact_match)
        for finding in actual:
            if finding.get("code") == "lifecycle_evidence_gap":
                combined = " ".join(
                    str(finding.get(field) or "")
                    for field in ("title", "summary")
                ).casefold()
                if "not proof" not in combined:
                    unsupported_causal_claims.append(
                        {
                            "case_id": case["case_id"],
                            "finding_id": finding.get("finding_id"),
                            "reason": "gap finding omits the explicit non-causal qualifier",
                        }
                    )
            if finding.get("evidence_grade") in {"inferred", "experimental"}:
                unsupported_causal_claims.append(
                    {
                        "case_id": case["case_id"],
                        "finding_id": finding.get("finding_id"),
                        "reason": "deterministic rules emitted a non-deterministic grade",
                    }
                )
        results.append(
            {
                "case_id": case["case_id"],
                "description": case["description"],
                "exact_match": exact_match,
                "expected": sorted(expected_signatures),
                "actual": sorted(actual_signatures),
                "missed": sorted(missed),
                "unexpected": sorted(unexpected),
            }
        )

    precision = (
        true_positive / (true_positive + false_positive)
        if true_positive + false_positive
        else 1.0
    )
    recall = (
        true_positive / (true_positive + false_negative)
        if true_positive + false_negative
        else 1.0
    )
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "metrics": {
            "case_count": len(results),
            "exact_matches": exact_matches,
            "exact_match_rate": exact_matches / len(results),
            "true_positive": true_positive,
            "false_positive": false_positive,
            "false_negative": false_negative,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "first_boundary_accuracy": exact_matches / len(results),
            "unsupported_causal_claim_count": len(unsupported_causal_claims),
        },
        "cases": results,
        "policy_audit": {
            "unsupported_causal_claims": unsupported_causal_claims,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=EXPERIMENT_DIR / "cases.jsonl")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()

    cases_path = arguments.cases.resolve()
    cases_bytes = cases_path.read_bytes()
    cases = _load_cases(cases_path)
    evaluation = _evaluate(cases)
    timestamp = datetime.now(timezone.utc)
    output_path = arguments.output
    if output_path is None:
        name = timestamp.strftime("runtime-diagnostics-%Y%m%dT%H%M%SZ.json")
        output_path = EXPERIMENT_DIR / "results" / name
    output_path = output_path.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    report = {
        "schema_version": "sri.experiment.runtime-diagnostics.v1",
        "created_at": timestamp.isoformat(),
        "experiment": {
            "name": "runtime-diagnostics-fault-injection",
            "diagnostic_engine": "deterministic-production-rules",
            "dataset_path": str(cases_path),
            "dataset_sha256": hashlib.sha256(cases_bytes).hexdigest(),
        },
        "environment": _environment(),
        **evaluation,
    }
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["metrics"], indent=2))
    print(f"Report: {output_path}")
    metrics = report["metrics"]
    gate_passed = (
        metrics["exact_match_rate"] == 1.0
        and metrics["unsupported_causal_claim_count"] == 0
    )
    print(f"Gate: {'PASS' if gate_passed else 'FAIL'}")
    return 0 if gate_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
