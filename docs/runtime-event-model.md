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

- internal source-instance session ID;
- upstream source session ID and a non-destructive correlation key;
- agent, model, project, and working directory;
- start and end time;
- source transcript location;
- ingestion completeness.

The internal `session_id` identifies one physical evidence stream, such as one
transcript file or one official-hook stream. `source_session_id` preserves the
logical identity reported by the Agent. Multiple physical streams may report
the same upstream ID; they remain separate sessions and share a
`correlation_key`. Correlation never authorizes one stream to overwrite or
erase another.

### SkillRun

- Skill identity and digest;
- independent occurrence identity within a turn;
- activation mode: explicit tool, UI selection, slash command, automatic,
  instruction evidence, unknown;
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
  "timestamp_origin": "source",
  "ingested_at": "2026-07-28T12:00:00.031Z",
  "clock_domain": "source_reported",
  "clock_uncertainty_ms": null,
  "timestamp_precision": "milliseconds",
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

`occurred_at` is not automatically a synchronized cross-source clock. Time
provenance is recorded separately:

- `timestamp_origin`: `source`, `adapter_fallback`, `collector_fallback`,
  `derived`, or `unknown`;
- `ingested_at`: local collector receipt/normalization time;
- `clock_domain`: the clock namespace when known, otherwise `unknown`;
- `clock_uncertainty_ms`: an uncertainty bound only when a source or measured
  clock-health signal supports it;
- `timestamp_precision`: reported or mechanically observable timestamp
  precision, otherwise `unknown`.

Legacy events retain `unknown` provenance rather than receiving fabricated
clock metadata. Cross-Agent absolute-time comparison requires compatible clock
domains and supported uncertainty; event presence alone is insufficient.

An event's existence and its relationship to a SkillRun are separate claims.
For example, a tool call can be Observed while the active-scope relationship
connecting it to a SkillRun is Derived.

## 5. Event types

### Session and turn

- `session.started`
- `session.ended`
- `session.compacted`
- `context.compaction_started`
- `context.compaction_completed`
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

`skill.activation_completed` closes the Agent's activation operation (for
example, the `Skill` tool call); it does not close the surrounding SkillRun.
The active Skill scope remains open for subsequent execution and artifacts
until a turn/session terminal event, explicit deactivation, activation failure,
or outcome boundary is observed.

An Agent UI selection may normalize to `skill.activated` only when the source
exposes an exact structured Skill identity, typed Skill attachment/message, or
versioned local metadata record. Prompt-text similarity is not an activation
signal. The source-specific entrypoint is retained as `activation_mode` and in
the evidence basis.

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

### Skill behavior constraints

Behavior conformance is a derived view over the current `SKILL.md` definition
and normalized runtime evidence. The MVP extracts only explicit, checkable
tool, resource, command, prohibition, and verification constraints. Each
constraint is reported as `satisfied`, `deviation`,
`expected_not_observed`, or `not_evaluable` and links to its source line and
lifecycle stage. Conditional applicability or redacted command arguments must
produce `not_evaluable`, never an invented failure. Constraint source text is
not persisted with the run.

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

## 6.1 Causal scope

Evidence certainty and causal permission are independent. Findings expose a
separate `causal_scope`:

| Scope | Allowed wording |
|---|---|
| `none` | descriptive boundary and evidence statements only |
| `source_assertion_only` | report that a source asserted attribution; do not present it as a validated effect |
| `experimental_estimate` | report a bounded effect estimate from a controlled experimental record |

Every deterministic single-Run diagnostic uses `none`, including an Observed
failure. Unknown scopes and claim kinds fail closed. A model confidence score
never expands causal scope.

## 7. Correlation precedence

Use this order:

1. explicit source parent/child ID;
2. explicit Skill attribution field;
3. source session and active Skill scope;
4. exact artifact path reported by a tool;
5. temporal adjacency plus matching path;
6. heuristic or model inference.

Levels 1–4 may usually be Derived. Levels 5–6 must include uncertainty and must never overwrite observed relationships.

Active Skill scope is persisted in the local evidence index rather than held
only in a Hook server process. This makes level-3 attribution deterministic
across native-sender, HTTP/queue fallback, and separate fail-open Hook
processes. A new observed request boundary clears an unclosed prior scope so a
missing terminal Hook cannot silently attribute the next turn to the old
Skill.

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

The initial relationship vocabulary includes:

- `source_parent` — deterministic source parent or call ID;
- `skill_scope` — direct Skill evidence or active Skill scope;
- `runtime_context` — request/outcome sharing the SkillRun turn boundary.

This separation allows re-normalization when an adapter changes without contaminating source evidence.

## 10. Collection checkpoint metadata

Collection progress is local control metadata, not a normalized runtime event
and not evidence that a source is complete. Each versioned adapter may expose
one current collection epoch with:

- a monotonically increasing adapter-local epoch identifier;
- `running`, `completed`, or `failed` state;
- source, changed-source, and removed-source counts;
- processed and failed-source counts;
- a privacy-preserving source high-watermark digest;
- start and end storage revisions;
- an explicit late-arrival count.

The persisted checkpoint must not contain source paths or raw source content.
A completed epoch means only that the adapter finished the source boundary it
observed. It does not upgrade any event evidence grade, prove that upstream
sources emitted every event, or make a dataset immutable. Dataset export must
bind a completed checkpoint to an immutable snapshot manifest; later arrivals
create a new dataset revision rather than silently modifying the frozen one.
When an observed source disappears, the next epoch records the removal without
silently deleting already reconstructed historical evidence. Source
availability and historical-run retention are separate states.

Checkpoint consumers interpret completion as a convergence protocol:

- `running` — the observed boundary is still being processed;
- `completed` with `late_arrival_count > 0` — catch-up is required;
- `completed` with zero late arrivals — candidate checkpoint only;
- frozen dataset revision — candidate checkpoint plus immutable snapshot and
  manifest.
