# UI information architecture

## 1. Experience goal

A developer should understand a Skill run in less than one minute, then be able to inspect exact evidence without leaving the UI.

The default UI is an audit and understanding surface. It does not ask the user to approve, block, or control agent execution.

## 2. Navigation model

```text
Runs
├── Run overview
│   ├── Narrative summary
│   ├── Skill Run Panorama
│   ├── Event timeline
│   └── Evidence inspector
├── Skills
│   └── Skill definition and observed usage
└── Settings
    ├── Agent adapters
    ├── Included projects
    ├── Privacy and redaction
    └── Data retention
```

The default route is the runs list, not a command input.

## 3. Runtime overview

The default Runs route pairs the SkillRun index with a boundary-first overview:

- aggregate the first observable boundary across SkillRuns;
- elevate a boundary shared by most runs as an adapter or telemetry coverage
  signal instead of duplicating it as hundreds of per-run alerts;
- rank the remaining attention queue by earliest observable boundary, then
  explicit failure and recency;
- keep every aggregate statement labeled as Derived;
- state that missing evidence is not proof that a Skill step failed.

This view answers “what deserves investigation now?” without turning the
product into a session dashboard or severity-only alert queue.

## 4. Runs list

Each row shows:

- start time;
- task or session title;
- agent and model;
- project;
- activated Skills;
- status;
- duration;
- evidence completeness.

Filters:

- agent;
- project;
- Skill;
- date;
- status;
- has errors;
- evidence grade.

## 5. Run overview

### Header

- run title;
- agent, model, project, time;
- status and duration;
- activated Skills;
- telemetry completeness;
- local/private indicator.

### Narrative summary

Example:

> The `pdf` Skill was explicitly activated. It loaded its main instructions and one reference, ran two scripts, created 11 page images, inspected three images, and produced a report. One referenced checklist was not observed. The session completed in 38 seconds.

Every sentence is assembled from evidence-backed facts and links to the corresponding nodes.

## 6. First Observable Boundary

Each SkillRun exposes the first lifecycle stage at which evidence becomes
unavailable before later activity. The boundary is a diagnostic starting
point, not a causal attribution. A system-wide concentration at one boundary
is reported separately from run-specific failures.

## 7. Skill Run Panorama

Primary stages:

```text
Request → Discovery → Activation → Instructions → Resources → Execution → Artifacts → Outcome
```

### Progressive collapse

Large runs must not produce unreadable graphs:

- collapse repeated file reads into `Files read ×12`;
- group tool calls by Skill and turn;
- group subagent internals until expanded;
- show only the critical path by default;
- allow “show all events” for expert inspection.

### Node types

| Node | Examples |
|---|---|
| Request | user prompt, resumed task |
| Skill | discovered, activated, failed |
| Instruction | `SKILL.md`, instruction block |
| Resource | script, reference, asset |
| Tool | Bash, Read, Write, MCP call |
| Subagent | Explore, reviewer, custom agent |
| Artifact | code file, image, PDF, report |
| Outcome | completed, failed, unknown, verified |

### Edge semantics

- solid line: observed source relationship;
- normal dashed line: derived relationship;
- dotted line: inferred relationship;
- experimental badge: paired evaluation result.

Edges must explain their basis on hover or selection.

## 8. Timeline

The timeline is the authoritative chronological view:

```text
10:21:03  Request received
10:21:04  Skill `pdf` activated
10:21:04  `pdf/SKILL.md` loaded
10:21:06  `references/layout.md` read
10:21:08  `scripts/render.py` executed
10:21:19  11 files created
10:21:23  Tool completed
```

Capabilities:

- filter by event type and Skill;
- jump between timeline and panorama nodes;
- highlight failures, retries, and long spans;
- show “not observed” and “unsupported” without treating them as failures.

## 9. Evidence inspector

Selecting any node opens a side panel with:

- human-readable explanation;
- status and duration;
- evidence grade;
- source adapter;
- source record locator;
- redacted input and output;
- affected files and artifacts;
- parent and child relationships;
- missing telemetry;
- confidence and basis for inference.

Raw JSON is available behind an explicit expansion control.

## 10. Compare and comparability mask

Comparison is available for same-Agent runs, cross-Agent runs, and explicit
Skill-version changes. Before showing a behavioral difference, the UI decides
comparability independently for:

- ordered lifecycle behavior;
- terminal outcome evidence;
- absolute time.

Task alignment, Skill definition, activation entrypoint, adapter capability,
terminal-state availability, and timestamp provenance can mask a dimension.
Masked dimensions remain visible for side-by-side evidence inspection, but do
not produce behavioral difference claims. Comparison never enables causal
attribution.

## 11. Inferred analysis

Inferred Analysis is a separate, visibly uncertain surface. It may explain a
finding or recommend the next investigation, but it:

- never changes normalized events, relationships, or deterministic findings;
- cites the evidence and missing signals that bounded the suggestion;
- labels confidence and the Inferred grade;
- abstains when no evidence-bounded suggestion is available;
- never claims that a Skill caused an outcome.

## 12. Evidence visual language

```text
● Observed      direct source evidence
◆ Derived       deterministic relationship
◇ Inferred      uncertain explanation
▣ Experimental  controlled evaluation
```

Do not rely on color alone. Use shape, text, and accessible labels.

## 13. Visual direction

- dark, restrained control-plane aesthetic;
- professional DAG canvas;
- compact timeline;
- strong node hierarchy;
- subtle animation for live events;
- clear detail panels.

The visual design must follow this product's observational, evidence-graded
semantics and must not introduce admission gates, enforcement controls, or
verification language unsupported by runtime evidence.

## 14. First-run experience

1. Detect supported agents.
2. Explain exactly which local paths will be read.
3. Let the user exclude projects.
4. Index existing runs.
5. Open the runs list with a short privacy statement.

No account, cloud connection, or task wrapper is required.

## 15. Empty and uncertainty states

Good empty states are part of product credibility:

- “No Skill activation observed in this session.”
- “Candidate matching is not exposed by this Codex adapter.”
- “This session appears incomplete.”
- “Token usage is unavailable from this source.”
- “A relationship is possible but cannot be established from current evidence.”
