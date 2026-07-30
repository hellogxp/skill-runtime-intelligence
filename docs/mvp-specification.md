# MVP specification

Version target: v0.1  
Theme: **Reconstruct what a Skill did**

## 1. MVP outcome

Given an existing or live local agent session, produce an accurate, evidence-graded Skill Run Panorama without modifying the agent, workspace, or model traffic.

## 2. Supported environments

Initial adapters:

- Claude Code
- Codex
- Qoder
- OpenCode

The architecture must allow additional adapters without changing the normalized event model.

## 3. Primary workflow

```text
Install or run locally
        ↓
Discover supported agent installations
        ↓
Index Skill metadata and local sessions
        ↓
Normalize source events
        ↓
Correlate Skill, resource, tool, subagent, and artifact evidence
        ↓
Open local runs UI
```

No task prompt is required to open the UI. The home page lists all known runs.

## 4. Functional requirements

### F1. Agent and Skill discovery

- Detect supported local agent installations.
- Scan user, project, and plugin Skill locations.
- Parse Agent Skills-compatible frontmatter.
- Record Skill source, path, digest, optional version, and compatibility.
- Report malformed or missing files without modifying them.

### F2. Session ingestion

- Import historical local sessions.
- Tail new local sessions when the format supports safe incremental reading.
- Preserve each physical evidence stream even when multiple sources report the
  same upstream session ID; correlate them without storage-side merging.
- Preserve source adapter name and source format version.
- Avoid ingesting credentials or unrelated files.
- Tolerate incomplete sessions and partial writes.

### F3. Runtime reconstruction

Reconstruct, when evidence exists:

- session and turn boundaries;
- explicit Skill invocation;
- direct command or slash invocation;
- instruction and resource reads;
- built-in and MCP tool calls;
- subagent start and completion;
- success, failure, interruption, and retry;
- file and artifact creation or modification;
- duration, token, and cost data exposed by the source.

### F4. Evidence correlation

- Correlate events using source IDs before timestamps.
- Preserve parent/child tool and subagent relationships.
- Connect file outcomes to tool calls only when evidence supports the relationship.
- Record missing telemetry explicitly.
- Label every relationship with an evidence grade.

### F5. Runs UI

- List all runs with time, agent, project, Skill, status, and duration.
- Render a progressively collapsed Skill Run Panorama.
- Render a chronological event timeline.
- Show a node inspector with source evidence.
- Filter by Skill, event type, status, and evidence grade.
- Display raw records only on demand.

### F6. Privacy

- Operate locally without an account.
- Keep network export disabled by default and require an explicit OTLP endpoint.
- Redact common credential patterns before persistence.
- Allow users to exclude projects and paths.
- Allow deletion of indexed run data without touching source transcripts.

## 5. Panorama stages

The normalized presentation follows these stages:

1. Request
2. Discovery
3. Activation
4. Instruction loading
5. Resource loading
6. Execution
7. Artifacts
8. Outcome

Stages with no evidence are shown as “not observed,” not “failed.”

## 6. Status semantics

| Status | Meaning |
|---|---|
| Observed | Source evidence exists |
| Completed | A source completion event exists |
| Failed | A source failure event exists |
| Interrupted | The source reports cancellation or interruption |
| Incomplete | The session ended without a matching completion event |
| Not observed | The collector lacks evidence |
| Unsupported | The adapter cannot currently observe this signal |

## 7. Non-functional requirements

- Indexing must not modify source agent files.
- Collection must be fail-open, bounded, and measured; failures must not block
  agent execution.
- Adapter parsing errors must not crash ingestion of other sessions.
- Raw, normalized, and inferred records must remain separable.
- UI rendering must remain usable for runs with thousands of events.
- Sensitive raw payloads must be collapsed and redacted by default.
- Evidence source must be inspectable for every displayed claim.

## 8. Acceptance scenarios

### A. Explicit Skill run

Given a session with an explicit Skill invocation and tool calls, the UI shows the Skill, resources, tools, duration, and outcome with source links.

### B. No Skill run

Given a session with no observed Skill invocation, the UI says “No Skill activation observed” and still displays agent tool activity separately.

### C. Missing resource

Given a Skill that references a file that is absent, discovery reports the missing file. The runtime view does not claim the file was loaded.

### D. Partial session

Given a truncated session, ingestion succeeds and labels the run incomplete.

### E. Unsupported signal

Given an adapter that cannot observe candidate matching, the UI shows “Unsupported,” not an inferred candidate list.

### F. Privacy

Given a tool payload containing a common secret pattern, the persisted normalized view contains a redacted value.

## 9. Explicitly deferred

- Model-internal why-not-triggered explanations when candidate signals are not
  emitted by the Agent.
- With-Skill/without-Skill paired evaluation.
- Static quality scoring.
- Security vulnerability scanning.
- Hosted collaboration and organizational dashboards.

The implemented local product may show evidence-bounded “not observed”
explanations, inferred description-overlap candidates, and direct static
definition comparison. None of these are presented as proof of model intent or
runtime conflict.
