"""Conservative Skill behavior-constraint extraction and run evaluation.

The evaluator intentionally supports only constraints that can be connected to
runtime evidence without interpreting arbitrary prose.  Unsupported natural-
language requirements remain outside the assessed set instead of being guessed.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


_NORMATIVE = re.compile(
    r"\b(?:must|shall|required|always|never|do not|don't|call|execute|run)\b"
    r"|(?:必须|务必|不得|禁止|不可|不要|始终|应当|需要|需调用|执行)",
    re.IGNORECASE,
)
_PROHIBITED = re.compile(
    r"\b(?:must not|never|do not|don't|prohibited|forbidden)\b"
    r"|(?:不得|禁止|不可|不要)",
    re.IGNORECASE,
)
_REQUIRED_CUE = re.compile(
    r"\b(?:must(?!\s+not)|shall|required|always)\b"
    r"|(?:必须|务必|始终|应当|需要|需调用)",
    re.IGNORECASE,
)
_CONDITIONAL = re.compile(
    r"\b(?:if|when|whenever|only when|scenario)\b|(?:如果|当|仅当|场景|时才)",
    re.IGNORECASE,
)
_TOOL_REF = re.compile(
    r"(?:<tool[^>]*>)?([A-Za-z][\w.-]*)::([A-Za-z][\w.-]*)(?:</tool>)?"
    r"|\b(mcp__[A-Za-z0-9_.-]+)\b"
)
_RESOURCE_REF = re.compile(
    r"`([^`]*(?:SKILL\.md|references?/[^`\s]+|scripts?/[^`\s]+|assets?/[^`\s]+))`",
    re.IGNORECASE,
)
_COMMAND_START = re.compile(
    r"^(?:\$\s*)?(a1|pytest|python(?:3)?|node|npm|pnpm|yarn|uv|git)\s+(.+)$",
    re.IGNORECASE,
)
_VERIFY_WORD = re.compile(
    r"\b(?:test|tests|verify|verification|validate|check)\b|(?:测试|验证|验收|检查)",
    re.IGNORECASE,
)
_MAX_SOURCE_BYTES = 512 * 1024
_MAX_CONSTRAINTS = 16


def _clean_markdown(value: str) -> str:
    value = re.sub(r"<!--.*?-->", " ", value)
    value = re.sub(r"</?tool[^>]*>", "", value)
    value = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", value)
    value = re.sub(r"[*_>#]", "", value)
    return re.sub(r"\s+", " ", value).strip(" |")


def _tool_target(match: re.Match[str]) -> Tuple[str, str]:
    if match.group(3):
        raw = match.group(3)
        return raw.split(".")[-1], raw
    server, tool = match.group(1), match.group(2)
    alias = f"mcp__{server.replace('-', '_')}.{tool}"
    return tool, alias


def _command_target(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip().strip("`").strip()
    match = _COMMAND_START.match(stripped)
    if not match:
        return None
    executable = match.group(1)
    arguments = match.group(2).split()
    label_parts = [executable, *arguments[:2]]
    return " ".join(label_parts), stripped


def _polarity_at(value: str, position: int) -> str:
    required = [match.start() for match in _REQUIRED_CUE.finditer(value[:position])]
    prohibited = [match.start() for match in _PROHIBITED.finditer(value[:position])]
    if prohibited and (not required or prohibited[-1] > required[-1]):
        return "prohibited"
    return "required"


def extract_behavior_constraints(
    content: str,
    *,
    source_path: str = "SKILL.md",
) -> List[Dict[str, Any]]:
    """Extract only explicit tool/resource/command obligations from SKILL.md."""

    constraints: List[Dict[str, Any]] = []
    seen = set()
    heading = ""
    recent_normative: List[Tuple[int, str]] = []
    in_frontmatter = False

    for line_number, raw_line in enumerate(content.splitlines(), start=1):
        stripped = raw_line.strip()
        if line_number == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("#"):
            heading = _clean_markdown(stripped)
            continue
        if not stripped or stripped == "```":
            continue

        clean = _clean_markdown(stripped)
        normative = bool(_NORMATIVE.search(clean))
        if normative:
            recent_normative.append((line_number, clean))
            recent_normative = recent_normative[-4:]
        context = clean
        if not normative and recent_normative:
            prior_line, prior = recent_normative[-1]
            if line_number - prior_line <= 5:
                context = f"{prior} {clean}"

        # Table rows conventionally encode ``scenario | action`` rules.  Their
        # applicability cannot be assumed merely because the action is named.
        conditional = bool(_CONDITIONAL.search(context) or "|" in stripped)

        candidates: List[Tuple[str, str, str, str]] = []
        if normative:
            for match in _TOOL_REF.finditer(stripped):
                label, target = _tool_target(match)
                candidates.append(
                    ("tool", label, target, _polarity_at(stripped, match.start()))
                )
            for match in _RESOURCE_REF.finditer(stripped):
                target = match.group(1)
                candidates.append(
                    (
                        "resource",
                        Path(target).name,
                        target,
                        _polarity_at(stripped, match.start()),
                    )
                )

        command = _command_target(stripped)
        if command and recent_normative:
            label, target = command
            kind = "verification" if _VERIFY_WORD.search(target) else "command"
            candidates.append((kind, label, target, "required"))

        for kind, label, target, polarity in candidates:
            key = (kind, target.lower(), polarity)
            if key in seen:
                continue
            seen.add(key)
            constraint_id = "constraint_" + hashlib.sha256(
                f"{source_path}:{line_number}:{kind}:{target}:{polarity}".encode()
            ).hexdigest()[:16]
            constraints.append(
                {
                    "constraint_id": constraint_id,
                    "kind": kind,
                    "polarity": polarity,
                    "target": target,
                    "target_label": label,
                    "conditional": conditional,
                    "stage": "resources" if kind == "resource" else "execution",
                    "source": {
                        "file": Path(source_path).name,
                        "line": line_number,
                        "section": heading,
                    },
                    "extraction_grade": "derived",
                }
            )
            if len(constraints) >= _MAX_CONSTRAINTS:
                return constraints
    return constraints


def _flatten_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)


def _evaluate_constraint(
    constraint: Dict[str, Any],
    run: Dict[str, Any],
) -> Dict[str, Any]:
    events = run.get("events") or []
    searchable = [
        text.lower()
        for event in events
        for text in (
            str(event.get("summary") or ""),
            *_flatten_strings(event.get("payload") or {}),
        )
        if text
    ]
    tool_names = {
        str((event.get("payload") or {}).get("tool_name") or "").lower()
        for event in events
        if event.get("stage") == "execution"
    }
    target = str(constraint["target"]).lower()
    label = str(constraint["target_label"]).lower()
    matched_event_ids: List[str] = []

    if constraint["kind"] == "tool":
        matched = any(
            name == target or name.endswith(f".{label}") or name.endswith(f"__{label}")
            for name in tool_names
        )
        if matched:
            matched_event_ids = [
                event.get("event_id")
                for event in events
                if str((event.get("payload") or {}).get("tool_name") or "").lower()
                in {
                    name for name in tool_names
                    if name == target
                    or name.endswith(f".{label}")
                    or name.endswith(f"__{label}")
                }
            ]
    elif constraint["kind"] == "resource":
        matched = any(target in value or label in value for value in searchable)
        if label == "skill.md" and any(
            event.get("event_type") == "instruction.loaded" for event in events
        ):
            matched = True
        if matched:
            matched_event_ids = [
                event.get("event_id")
                for event in events
                if event.get("stage") in {"instructions", "resources"}
            ]
    else:
        matched = any(target in value for value in searchable)
        if constraint["kind"] == "verification" and any(
            event.get("event_type") == "outcome.verified" for event in events
        ):
            matched = True
            matched_event_ids = [
                event.get("event_id")
                for event in events
                if event.get("event_type") == "outcome.verified"
            ]

    if constraint["polarity"] == "prohibited":
        if matched:
            status = "deviation"
            basis = "A prohibited target appears in the observed runtime evidence."
        elif constraint["conditional"] or run.get("session_completeness") != "complete":
            status = "not_evaluable"
            basis = "The prohibition trigger or complete execution boundary is unavailable."
        else:
            status = "satisfied"
            basis = "The prohibited target was not present in the complete observable boundary."
    elif matched:
        status = "satisfied"
        basis = "The expected target appears in the observed runtime evidence."
    elif constraint["kind"] in {"command", "verification"}:
        status = "not_evaluable"
        basis = "Command arguments are redacted, so this requirement cannot be matched safely."
    elif constraint["conditional"]:
        status = "not_evaluable"
        basis = "The instruction is conditional and trigger applicability is not observable."
    elif run.get("session_completeness") != "complete":
        status = "not_evaluable"
        basis = "The source session is incomplete, so absence is not evidence of deviation."
    else:
        status = "expected_not_observed"
        basis = "The required target was not found in the complete observable boundary."

    return {
        **constraint,
        "status": status,
        "basis": basis,
        "evidence_grade": "observed" if matched else "derived",
        "event_ids": [event_id for event_id in matched_event_ids if event_id],
    }


def assess_skill_behavior(run: Dict[str, Any]) -> Dict[str, Any]:
    """Build a privacy-safe, evidence-bounded behavior assessment for a run."""

    source_path = str(run.get("source_path") or "")
    result: Dict[str, Any] = {
        "status": "definition_unavailable",
        "source_status": "unavailable",
        "source_file": "SKILL.md",
        "constraints": [],
        "counts": {
            "total": 0,
            "checked": 0,
            "satisfied": 0,
            "deviations": 0,
            "expected_not_observed": 0,
            "not_evaluable": 0,
        },
        "first_deviation_stage": None,
        "verifier_expected": False,
        "evidence_grade": "derived",
        "limitation": "No readable current Skill definition is available.",
    }
    if not source_path or source_path.startswith("collector://"):
        return result
    path = Path(source_path)
    try:
        if not path.is_file() or path.stat().st_size > _MAX_SOURCE_BYTES:
            return result
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return result

    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    constraints = [
        _evaluate_constraint(item, run)
        for item in extract_behavior_constraints(content, source_path=source_path)
    ]
    counts = {
        "total": len(constraints),
        "checked": sum(
            item["status"] in {"satisfied", "deviation", "expected_not_observed"}
            for item in constraints
        ),
        "satisfied": sum(item["status"] == "satisfied" for item in constraints),
        "deviations": sum(item["status"] == "deviation" for item in constraints),
        "expected_not_observed": sum(
            item["status"] == "expected_not_observed" for item in constraints
        ),
        "not_evaluable": sum(item["status"] == "not_evaluable" for item in constraints),
    }
    if counts["deviations"]:
        status = "deviation"
    elif counts["expected_not_observed"]:
        status = "expected_not_observed"
    elif counts["checked"] and counts["not_evaluable"]:
        status = "partially_checked"
    elif counts["checked"]:
        status = "satisfied_observed_scope"
    elif constraints:
        status = "not_evaluable"
    else:
        status = "no_checkable_constraints"

    first_deviation = next(
        (
            item
            for item in constraints
            if item["status"] in {"deviation", "expected_not_observed"}
        ),
        None,
    )
    exact_definition = not run.get("digest") or digest == run.get("digest")
    return {
        **result,
        "status": status,
        "source_status": "current_exact" if exact_definition else "current_changed",
        "constraints": constraints,
        "counts": counts,
        "first_deviation_stage": first_deviation.get("stage") if first_deviation else None,
        "verifier_expected": any(item["kind"] == "verification" for item in constraints),
        "limitation": (
            "Constraints come from the current Skill definition and are evaluated "
            "only where normalized runtime evidence supports an exact match."
        ),
    }
