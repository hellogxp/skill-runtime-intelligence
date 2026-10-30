#!/usr/bin/env python3
"""Evaluate Codex raw-source reconstruction against a reviewed golden corpus."""

import argparse
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import load_jsonl, sha256_path, write_report
from skill_runtime_intelligence.adapters.codex import ADAPTER_VERSION, CodexAdapter
from skill_runtime_intelligence.discovery import parse_skill


def _record(index: int, outer_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "timestamp": f"2026-07-29T06:00:{index:02d}Z",
        "type": outer_type,
        "payload": payload,
    }


def _call(index: int, name: str, text: str, call_id: str) -> Dict[str, Any]:
    return _record(
        index,
        "response_item",
        {
            "type": "function_call",
            "name": name,
            "call_id": call_id,
            "input": {"cmd": text},
        },
    )


def _materialize(case: Dict[str, Any], root: Path):
    definitions = []
    for name in ("pdf", "sheets"):
        skill_file = root / "skills" / name / "SKILL.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text(
            f"---\nname: {name}\ndescription: Fixture {name} Skill\n---\nFixture.\n",
            encoding="utf-8",
        )
        definitions.append(parse_skill(skill_file))
    paths = {definition.name: Path(definition.source_path) for definition in definitions}
    records = [
        _record(0, "session_meta", {"id": case["case_id"], "cwd": str(root)}),
        _record(1, "event_msg", {"type": "task_started", "turn_id": "turn-1"}),
    ]
    scenario = case["scenario"]
    malformed = False
    if scenario == "instruction":
        records.append(_call(2, "exec_command", f"sed -n 1,120p {paths['pdf']}", "c1"))
    elif scenario == "explicit":
        records.append(_call(2, "skill", "pdf", "c1"))
    elif scenario == "script":
        records.append(
            _call(
                2,
                "exec_command",
                f"python {paths['pdf'].parent / 'scripts' / 'render.py'}",
                "c1",
            )
        )
    elif scenario == "relative_script":
        records.append(
            _call(
                2,
                "exec_command",
                "python skills/pdf/scripts/render.py",
                "c1",
            )
        )
    elif scenario == "path_collision":
        records.append(
            _call(
                2,
                "exec_command",
                f"python {paths['pdf'].parent}-backup/scripts/render.py",
                "c1",
            )
        )
    elif scenario == "name_collision":
        records.append(_call(2, "skill", "pdf-backup", "c1"))
    elif scenario == "scope":
        records.extend(
            [
                _call(2, "exec_command", f"sed -n 1,120p {paths['pdf']}", "c1"),
                _record(
                    3,
                    "response_item",
                    {"type": "function_call_output", "call_id": "c1", "output": "ok"},
                ),
                _call(4, "exec_command", "python deterministic_workload.py", "c2"),
                _record(
                    5,
                    "response_item",
                    {"type": "function_call_output", "call_id": "c2", "output": "ok"},
                ),
            ]
        )
    elif scenario == "interrupted":
        records.extend(
            [
                _call(2, "exec_command", f"sed -n 1,120p {paths['pdf']}", "c1"),
                _record(
                    3,
                    "event_msg",
                    {
                        "type": "turn_aborted",
                        "turn_id": "turn-1",
                        "reason": "fixture",
                    },
                ),
            ]
        )
    elif scenario == "malformed":
        malformed = True
        records.append(_call(2, "exec_command", f"sed -n 1,120p {paths['pdf']}", "c1"))
    elif scenario == "two_skills":
        records.extend(
            [
                _call(2, "exec_command", f"sed -n 1,120p {paths['pdf']}", "c1"),
                _call(3, "exec_command", f"sed -n 1,120p {paths['sheets']}", "c2"),
            ]
        )
    else:
        raise ValueError(f"Unknown scenario: {scenario}")
    if scenario != "interrupted":
        records.append(
            _record(9, "event_msg", {"type": "task_complete", "turn_id": "turn-1"})
        )
    source = root / f"{case['case_id']}.jsonl"
    body = "".join(json.dumps(record) + "\n" for record in records)
    if malformed:
        body = body.splitlines(True)[0] + "{malformed\n" + "".join(
            body.splitlines(True)[1:]
        )
    source.write_text(body, encoding="utf-8")
    return source, definitions


def _multiset_metrics(expected: Counter, actual: Counter) -> Dict[str, int]:
    matched = expected & actual
    return {
        "tp": sum(matched.values()),
        "fp": sum((actual - expected).values()),
        "fn": sum((expected - actual).values()),
    }


def _evaluate_case(case: Dict[str, Any], root: Path) -> Dict[str, Any]:
    source, definitions = _materialize(case, root)
    session, raw, events, runs = CodexAdapter(root).parse(source, definitions)
    names = {definition.skill_id: definition.name for definition in definitions}
    actual_runs = Counter(
        (
            names.get(run["skill_id"], "unknown"),
            run["activation_mode"],
            run["evidence_grade"],
            run["status"],
        )
        for run in runs
    )
    actual_events = Counter(
        (
            event["event_type"],
            names.get(event.get("skill_id"), "unknown"),
            event["evidence_grade"],
            event.get("payload", {}).get("resource_kind"),
        )
        for event in events
        if event.get("skill_id")
    )
    expected_runs = Counter(tuple(item) for item in case["expect"]["skill_runs"])
    expected_events = Counter(tuple(item) for item in case["expect"]["skill_events"])
    run_counts = _multiset_metrics(expected_runs, actual_runs)
    event_counts = _multiset_metrics(expected_events, actual_events)
    expected_attributed = case["expect"].get("attributed_tool_events")
    actual_attributed = sum(
        event["event_type"] in {"tool.started", "tool.completed"}
        and bool(event.get("skill_run_id"))
        for event in events
    )
    scalar_checks = {
        "session_status": session["status"] == case["expect"]["session_status"],
        "completeness": session["completeness"] == case["expect"]["completeness"],
        "attributed_tool_events": (
            True
            if expected_attributed is None
            else actual_attributed == expected_attributed
        ),
    }
    exact = (
        all(value == 0 for value in (run_counts["fp"], run_counts["fn"]))
        and all(value == 0 for value in (event_counts["fp"], event_counts["fn"]))
        and all(scalar_checks.values())
    )
    return {
        "case_id": case["case_id"],
        "exact_match": exact,
        "run_counts": run_counts,
        "event_counts": event_counts,
        "scalar_checks": scalar_checks,
        "expected_runs": sorted(expected_runs.elements()),
        "actual_runs": sorted(actual_runs.elements()),
        "expected_skill_events": sorted(
            expected_events.elements(), key=lambda value: tuple(str(x) for x in value)
        ),
        "actual_skill_events": sorted(
            actual_events.elements(), key=lambda value: tuple(str(x) for x in value)
        ),
        "raw_record_count": len(raw),
        "normalized_event_count": len(events),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=Path, default=EXPERIMENT_DIR / "cases.jsonl")
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    cases = load_jsonl(arguments.cases)
    with tempfile.TemporaryDirectory(prefix="sri-e1-") as directory:
        root = Path(directory)
        results = [
            _evaluate_case(case, root / case["case_id"])
            for case in cases
        ]
    total_events = {"tp": 0, "fp": 0, "fn": 0}
    for result in results:
        for layer in ("run_counts", "event_counts"):
            for key in total_events:
                total_events[key] += result[layer][key]
    precision = total_events["tp"] / max(
        1, total_events["tp"] + total_events["fp"]
    )
    recall = total_events["tp"] / max(
        1, total_events["tp"] + total_events["fn"]
    )
    metrics = {
        "case_count": len(results),
        "exact_matches": sum(result["exact_match"] for result in results),
        "exact_match_rate": sum(result["exact_match"] for result in results)
        / len(results),
        **total_events,
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        ),
    }
    report = {
        "schema_version": "sri.experiment.adapter-reconstruction.v1",
        "experiment": {
            "name": "codex-adapter-golden-corpus",
            "adapter": "codex",
            "adapter_version": ADAPTER_VERSION,
            "dataset_path": str(arguments.cases.resolve()),
            "dataset_sha256": sha256_path(arguments.cases),
            "evidence_policy": (
                "Observed Skill events and Derived SkillRun attribution are scored "
                "as separate labeled fields."
            ),
        },
        "metrics": metrics,
        "cases": results,
    }
    output = write_report(
        EXPERIMENT_DIR, "adapter-reconstruction", report, arguments.output
    )
    print(json.dumps(metrics, indent=2))
    print(f"Report: {output}")
    passed = metrics["exact_match_rate"] == 1.0
    print(f"Gate: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
