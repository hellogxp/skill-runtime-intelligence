# Runtime event model

## 1. Purpose

Agent products expose different hooks, transcript schemas, and naming conventions. The runtime event model provides a stable, Skill-specific representation while preserving access to original source evidence.

## 2. Design rules

1. Source events are immutable.
2. Normalization never discards source identity.
3. Absence of evidence is not evidence of failure.
4. Inference is stored separately from observation.
5. Causal effectiveness is experimental, never inferred from one trace.
6. Adapter-specific fields may be retained as extensions.

## 3. Core entities

```text
AgentInstallation
    ├── SkillDefinition
    └── Session
          ├── Turn
          └── SkillRun
                ├── ResourceAccess
                ├── ToolExecution
                ├── SubagentRun
                ├── Artifact
                └── Outcome
```

### AgentInstallation

- agent type and version;
- configuration root;
- detected capabilities;
- adapter and adapter version.

### SkillDefinition

- stable local ID;
- name and description;
- source kind: user, project, plugin, bundled, unknown;
- absolute source path;
- content digest;
- declared compatibility and allowed tools;
- references to scripts, references, and assets.

### Session

- source session ID;
- agent, model, project, and working directory;
- start and end time;
- source transcript location;
- ingestion completeness.

### SkillRun

- Skill identity and digest;
- activation mode: explicit tool, slash command, automatic, inferred, unknown;
- activation and end events;
- evidence grade;
- status.

## 4. Event envelope

Every normalized event should support:

```json
{
  "event_id": "evt_local_unique",
  "event_type": "tool.completed",
  "occurred_at": "2026-07-28T12:00:00.000Z",
  "session_id": "session_source_id",
  "turn_id": "turn_source_id",
  "skill_run_id": "optional_skill_run_id",
  "parent_event_id": "optional_parent",
  "source": {
    "adapter": "claude-code",
    "adapter_version": "0.1.0",
    "record_locator": "opaque locator",
    "source_event_id": "toolu_..."
  },
  "evidence": {
    "grade": "observed",
    "confidence": 1.0,
    "basis": "PostToolUse event"
  },
  "payload": {}
}
```

Raw source content should not be duplicated into every normalized event. Store an opaque locator and a redacted summary.

## 5. Event types

### Session and turn

- `session.started`
- `session.ended`
- `session.compacted`
- `turn.started`
- `turn.completed`
- `turn.failed`

### Skill lifecycle

- `skill.discovered`
- `skill.discovery_failed`
- `skill.activated`
- `skill.activation_completed`
- `skill.activation_failed`
- `skill.deactivated`

Do not emit `skill.considered` unless the source explicitly provides a candidate event. Similarity analysis belongs in the inference layer.

### Instructions and resources

- `instruction.loaded`
- `resource.read`
- `resource.executed`
- `resource.missing`
- `resource.load_failed`

Resource kinds:

- `skill_body`
- `script`
- `reference`
- `asset`
- `other`

### Tools and subagents

- `tool.requested`
- `tool.started`
- `tool.completed`
- `tool.failed`
- `tool.denied`
- `subagent.started`
- `subagent.completed`
- `subagent.failed`

### Workspace and artifacts

- `file.read`
- `file.created`
- `file.modified`
- `file.deleted`
- `artifact.produced`
- `artifact.inspected`

### Outcomes

- `outcome.reported`
- `outcome.verified`
- `outcome.unknown`

`outcome.reported` is an agent or source assertion. `outcome.verified` requires an independent result such as a deterministic test or explicit user-provided evaluation.

## 6. Evidence model

```text
Observed
   ↓ deterministic transformation
Derived

Observed + analysis model
   ↓ uncertain explanation
Inferred

Controlled paired trials
   ↓ statistical estimate
Experimental
```

### Observed example

The source transcript contains a `Skill` tool call for `pdf`.

### Derived example

A `Write` tool result reports `/tmp/page-01.png`; the artifact node is linked to that tool execution.

### Inferred example

The user request and Skill description share distinctive PDF-layout terms, which may explain automatic activation.

### Experimental example

Matched tasks run repeatedly with and without the Skill show a measured pass-rate delta.

## 7. Correlation precedence

Use this order:

1. explicit source parent/child ID;
2. explicit Skill attribution field;
3. source session and active Skill scope;
4. exact artifact path reported by a tool;
5. temporal adjacency plus matching path;
6. heuristic or model inference.

Levels 1–4 may usually be Derived. Levels 5–6 must include uncertainty and must never overwrite observed relationships.

## 8. Adapter contract

Each adapter declares:

- supported agent and versions;
- discoverable Skill locations;
- supported event signals;
- fields that are measured versus estimated;
- known schema limitations;
- redaction behavior;
- fixtures for sanitized real transcripts.

Adapter output is validated against the normalized schema. Unsupported signals remain absent and are surfaced as unsupported capabilities.

## 9. Storage separation

Recommended logical layers:

```text
raw_source_records
        ↓
normalized_events
        ↓
derived_relationships
        ↓
inferences
        ↓
experimental_results
```

This separation allows re-normalization when an adapter changes without contaminating source evidence.

