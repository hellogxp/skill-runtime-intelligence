#!/usr/bin/env python3
"""Create a deterministic, sanitized SkillRun for documentation screenshots."""

import argparse
from pathlib import Path
from typing import Dict, List, Optional

from skill_runtime_intelligence.collector import normalize_collector_payload
from skill_runtime_intelligence.storage import Storage


SKILL = {
    "name": "release-notes",
    "description": "Generate evidence-backed release notes from verified changes.",
    "source_path": "/demo/skills/release-notes/SKILL.md",
    "source_kind": "project",
}
SOURCE = {
    "adapter": "example-agent",
    "adapter_version": "1.4.0",
    "collection_mode": "official_hook",
}
CONTEXT = {
    "title": "Prepare the v0.1 release notes and verify referenced changes",
    "cwd": "/workspace/example-product",
    "model": "example-model",
    "agent_version": "1.4.0",
}


def event(
    index: int,
    event_type: str,
    summary: str,
    *,
    skill: bool = True,
    parent: str = "",
    payload: Optional[Dict] = None,
) -> dict:
    event_id = f"demo-{index:02d}"
    envelope = {
        "event_id": event_id,
        "event_type": event_type,
        "occurred_at": f"2026-07-29T09:24:{index:02d}Z",
        "session_id": "demo-session-release",
        "turn_id": "turn-release",
        "run_token": "release-run",
        "summary": summary,
        "context": CONTEXT,
        "source": {
            **SOURCE,
            "source_event_id": event_id,
            "record_locator": f"example-agent:event:{index}",
        },
        "evidence": {
            "grade": "observed",
            "confidence": 1.0,
            "basis": "Official runtime event from the example adapter",
        },
        "payload": payload or {},
    }
    if skill:
        envelope["skill"] = SKILL
        envelope["activation_mode"] = "explicit_tool"
    if parent:
        envelope["parent_event_id"] = parent
    return envelope


def build_events() -> List[Dict]:
    return [
        event(1, "session.started", "Agent session started", skill=False),
        event(2, "turn.started", "Release documentation request received", skill=False),
        event(3, "skill.discovered", "release-notes definition discovered"),
        event(4, "skill.activated", "release-notes explicitly activated"),
        event(
            5,
            "instruction.loaded",
            "Loaded release-notes/SKILL.md",
            parent="demo-04",
            payload={"resource_kind": "skill_body", "path": "release-notes/SKILL.md"},
        ),
        event(
            6,
            "resource.read",
            "Loaded references/release-policy.md",
            parent="demo-05",
            payload={"resource_kind": "reference", "path": "references/release-policy.md"},
        ),
        event(
            7,
            "tool.started",
            "Inspect verified change manifest",
            parent="demo-06",
            payload={"tool_name": "Read"},
        ),
        event(
            8,
            "subagent.started",
            "Cross-check documentation links",
            parent="demo-07",
            payload={"tool_name": "reviewer"},
        ),
        event(
            9,
            "subagent.completed",
            "Documentation link review completed",
            parent="demo-08",
            payload={"tool_name": "reviewer"},
        ),
        event(
            10,
            "tool.completed",
            "Verified change manifest inspected",
            parent="demo-07",
            payload={"tool_name": "Read"},
        ),
        event(
            11,
            "file.created",
            "Created docs/releases/v0.1.md",
            parent="demo-10",
            payload={"path": "docs/releases/v0.1.md", "change_kind": "created"},
        ),
        event(
            12,
            "artifact.inspected",
            "Release notes checked against source evidence",
            parent="demo-11",
            payload={"path": "docs/releases/v0.1.md", "artifact_kind": "markdown"},
        ),
        event(
            13,
            "outcome.verified",
            "Release notes produced and evidence links verified",
            parent="demo-12",
        ),
        event(14, "turn.completed", "Agent turn completed", skill=False),
        event(15, "session.ended", "Agent session completed", skill=False),
    ]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("database", type=Path)
    args = parser.parse_args()
    args.database.parent.mkdir(parents=True, exist_ok=True)
    args.database.unlink(missing_ok=True)
    storage = Storage(args.database)
    try:
        result = storage.append_collector_events(
            normalize_collector_payload(build_events())
        )
        runs = storage.list_skill_runs()
    finally:
        storage.close()
    print(
        f"created {args.database} with {result['accepted']} events "
        f"and {len(runs)} SkillRun"
    )


if __name__ == "__main__":
    main()
