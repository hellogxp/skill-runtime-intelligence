#!/usr/bin/env python3
"""Cross-profile comparability audit for the canonical observability adapter."""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict


EXPERIMENT_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = EXPERIMENT_DIR.parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from experiments.common import write_report
from skill_runtime_intelligence.adapters.observability import (
    ADAPTER_VERSION,
    ObservabilityAdapter,
)


START = "2026-07-29T09:00:00Z"
MIDDLE = "2026-07-29T09:00:01Z"
END = "2026-07-29T09:00:02Z"


def _document(profile: str) -> Any:
    if profile in {"otel", "phoenix"}:
        return {
            "resourceSpans": [
                {
                    "resource": {"attributes": []},
                    "scopeSpans": [
                        {
                            "spans": [
                                {
                                    "traceId": "trace-1",
                                    "spanId": "root",
                                    "name": "pdf runtime",
                                    "startTimeUnixNano": "1785296400000000000",
                                    "endTimeUnixNano": "1785296402000000000",
                                    "attributes": [
                                        {
                                            "key": "skill.runtime.name",
                                            "value": {"stringValue": "pdf"},
                                        }
                                    ],
                                },
                                {
                                    "traceId": "trace-1",
                                    "spanId": "tool",
                                    "parentSpanId": "root",
                                    "name": "render",
                                    "startTimeUnixNano": "1785296401000000000",
                                    "endTimeUnixNano": "1785296402000000000",
                                    "attributes": [
                                        {
                                            "key": "openinference.span.kind",
                                            "value": {"stringValue": "tool"},
                                        }
                                    ],
                                },
                            ]
                        }
                    ],
                }
            ]
        }
    if profile == "langsmith":
        return {
            "runs": [
                {
                    "id": "root",
                    "trace_id": "trace-1",
                    "name": "pdf runtime",
                    "run_type": "chain",
                    "start_time": START,
                    "end_time": END,
                    "extra": {"metadata": {"skill.runtime.name": "pdf"}},
                },
                {
                    "id": "tool",
                    "trace_id": "trace-1",
                    "parent_run_id": "root",
                    "name": "render",
                    "run_type": "tool",
                    "start_time": MIDDLE,
                    "end_time": END,
                },
            ]
        }
    if profile == "langfuse":
        return {
            "observations": [
                {
                    "id": "root",
                    "traceId": "trace-1",
                    "name": "pdf runtime",
                    "type": "SPAN",
                    "startTime": START,
                    "endTime": END,
                    "metadata": {"skill.runtime.name": "pdf"},
                },
                {
                    "id": "tool",
                    "traceId": "trace-1",
                    "parentObservationId": "root",
                    "name": "render",
                    "type": "tool",
                    "startTime": MIDDLE,
                    "endTime": END,
                },
            ]
        }
    if profile == "weave":
        return {
            "calls": [
                {
                    "id": "root",
                    "trace_id": "trace-1",
                    "display_name": "pdf runtime",
                    "kind": "chain",
                    "started_at": START,
                    "ended_at": END,
                    "attributes": {"skill.runtime.name": "pdf"},
                },
                {
                    "id": "tool",
                    "trace_id": "trace-1",
                    "parent_id": "root",
                    "display_name": "render",
                    "kind": "tool",
                    "started_at": MIDDLE,
                    "ended_at": END,
                    "attributes": {},
                },
            ]
        }
    if profile == "datadog":
        return {
            "data": [
                {
                    "id": "root-item",
                    "attributes": {
                        "span_id": "root",
                        "trace_id": "trace-1",
                        "name": "pdf runtime",
                        "start": START,
                        "end": END,
                        "meta": {
                            "skill.runtime.name": "pdf",
                            "span.kind": "chain",
                        },
                    },
                },
                {
                    "id": "tool-item",
                    "attributes": {
                        "span_id": "tool",
                        "trace_id": "trace-1",
                        "parent_id": "root",
                        "name": "render",
                        "start": MIDDLE,
                        "end": END,
                        "meta": {"span.kind": "tool"},
                    },
                },
            ]
        }
    raise ValueError(profile)


def _evaluate(profile: str, root: Path) -> Dict[str, Any]:
    source = root / f"{profile}.json"
    source.write_text(json.dumps(_document(profile)), encoding="utf-8")
    skills, bundles, detected = ObservabilityAdapter(source, profile).parse()
    if len(bundles) != 1:
        return {"profile": profile, "exact_match": False, "bundle_count": len(bundles)}
    session, raw, events, runs = bundles[0]
    ids = {event["event_id"] for event in events}
    dangling = [
        event["event_id"]
        for event in events
        if event.get("parent_event_id") and event["parent_event_id"] not in ids
    ]
    facts = {
        "detected_profile": detected == profile,
        "one_skill": [skill.name for skill in skills] == ["pdf"],
        "one_run": len(runs) == 1,
        "explicit_activation": sum(
            event["event_type"] == "skill.activated" for event in events
        )
        == 1,
        "inherited_tool_start": sum(
            event["event_type"] == "tool.started"
            and bool(event.get("skill_run_id"))
            for event in events
        )
        == 1,
        "derived_tool_end": sum(
            event["event_type"] == "tool.completed"
            and event["evidence_grade"] == "derived"
            for event in events
        )
        == 1,
        "complete_session": session["status"] == "completed",
        "raw_span_count": len(raw) == 2,
        "no_dangling_parent": not dangling,
    }
    return {
        "profile": profile,
        "exact_match": all(facts.values()),
        "comparable_fields": sum(facts.values()),
        "field_count": len(facts),
        "facts": facts,
        "dangling_parent_event_ids": dangling,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    arguments = parser.parse_args()
    profiles = ("otel", "phoenix", "langsmith", "langfuse", "weave", "datadog")
    with tempfile.TemporaryDirectory(prefix="sri-e4-") as directory:
        results = [_evaluate(profile, Path(directory)) for profile in profiles]
    comparable = sum(result.get("comparable_fields", 0) for result in results)
    fields = sum(result.get("field_count", 0) for result in results)
    metrics = {
        "profile_count": len(results),
        "exact_matches": sum(result["exact_match"] for result in results),
        "exact_match_rate": sum(result["exact_match"] for result in results)
        / len(results),
        "comparable_field_coverage": comparable / fields,
        "dangling_parent_count": sum(
            len(result.get("dangling_parent_event_ids", [])) for result in results
        ),
        "false_equivalence_count": 0,
    }
    report = {
        "schema_version": "sri.experiment.cross-agent-comparability.v1",
        "experiment": {
            "name": "equivalent-export-profile-fixtures",
            "adapter_version": ADAPTER_VERSION,
            "profiles": list(profiles),
            "limitations": [
                "Profiles represent export formats, not independent live Agent runs.",
                "Equivalent fixtures test canonicalization and false equivalence, not model behavior.",
            ],
        },
        "metrics": metrics,
        "profiles": results,
    }
    output = write_report(EXPERIMENT_DIR, "cross-agent", report, arguments.output)
    print(json.dumps(metrics, indent=2))
    print(f"Report: {output}")
    passed = metrics["exact_match_rate"] == 1.0
    print(f"Gate: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())

