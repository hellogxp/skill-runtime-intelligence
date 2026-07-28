# Product definition

Status: approved direction  
Date: 2026-07-28  
Working category: **Agent Skill Runtime Intelligence**

## 1. One-sentence definition

Agent Skill Runtime Intelligence is a local-first, read-only developer tool that reconstructs how an Agent Skill was discovered, activated, loaded, executed, and connected to observable results.

## 2. User problem

Agent Skills use progressive disclosure:

1. metadata is made available for discovery;
2. full instructions are loaded after activation;
3. references, scripts, and assets are loaded on demand.

Each boundary can fail silently. A developer may see a plausible final answer while remaining unable to determine:

- whether the Skill was visible to the agent;
- whether the request matched the Skill;
- whether full instructions were loaded;
- whether required resources were read or executed;
- which actions occurred while the Skill was active;
- whether a failure came from the Skill, agent harness, model, environment, or task;
- whether the Skill produced measurable value.

Generic LLM tracing shows model and tool spans but does not make the Skill lifecycle the primary abstraction.

## 3. Target users

### Primary

- Individual Skill authors debugging local Skills.
- Plugin maintainers supporting Skills across multiple agent products.
- Teams maintaining shared Skills for internal workflows.

### Secondary

- Researchers evaluating Skill activation and effectiveness.
- Platform engineers diagnosing agent-harness regressions.
- Security reviewers inspecting runtime behavior without enabling enforcement.

## 4. Jobs to be done

### During development

> When I edit a Skill, show me whether the target agent can discover and activate it, and what it actually does.

### During debugging

> When a Skill appears not to work, identify the first observable lifecycle boundary that failed.

### During maintenance

> When a model, harness, or Skill version changes, show me how behavior changed.

### During evaluation

> When I need to know whether a Skill helps, run controlled paired evaluations and separate measured effect from runtime correlation.

## 5. Core product experience

The product opens on a list of Skill runs. Selecting a run reveals:

1. a concise narrative summary;
2. a Skill Run Panorama;
3. a trusted event timeline;
4. a node inspector with source evidence;
5. files and artifacts associated with the run;
6. explicit uncertainty and missing telemetry.

The default answer should be understandable without reading raw JSON:

> The `pdf` Skill was discovered and explicitly activated. It loaded `SKILL.md` and one reference, executed two scripts, created 11 page images, inspected three images, and produced a report. One referenced checklist was not observed. The run completed in 38 seconds.

## 6. Data sources

| Source | What it provides | Collection mode |
|---|---|---|
| Skill directories | metadata, instructions, scripts, references, assets | Filesystem scan |
| Agent hooks/events | lifecycle, tools, errors, subagents, timing | Local passive hook where supported |
| Session transcripts | messages, tool calls/results, ordering, metadata | Read-only import or tail |
| Workspace state | file changes, Git diff, reports, artifacts | Read-only observation |
| Evaluation results | repeated paired outcomes | Explicit opt-in experiment |

## 7. Evidence grades

### Observed

Directly encoded in a source event or file:

- an explicit Skill tool invocation;
- reading `SKILL.md`;
- a tool input and output;
- a process exit code;
- a file creation event.

### Derived

Deterministically connected from observed evidence:

- a file was produced by a particular tool call;
- a subagent was launched by a particular parent call;
- a duration is the difference between paired start and end events.

### Inferred

An uncertain explanation:

- a Skill may have matched because its description contains terms from the request;
- a missing resource read may explain an incomplete output;
- two Skills may have overlapping trigger descriptions.

Every inference must include its basis and confidence. “Unknown” is preferable to unsupported certainty.

### Experimental

An effect estimated through controlled repeated evaluation:

- pass-rate delta with and without a Skill;
- token or latency overhead under matched conditions;
- confidence intervals or paired-test results.

## 8. Product boundaries

### In scope

- Skill lifecycle observability.
- Runtime evidence reconstruction.
- Local run replay and comparison.
- Skill-specific activation diagnosis.
- Controlled effectiveness evaluation in a later release.

### Out of scope for the MVP

- Controlling the agent loop.
- Blocking tools or enforcing policy.
- Replacing Claude Code, Codex, or OpenCode.
- Proxying LLM API traffic.
- A public Skill marketplace or package registry.
- Enterprise approval workflows.
- General-purpose LLM observability.
- Automated causal claims from a single run.

## 9. Differentiation

The product is not differentiated by collecting spans or drawing a DAG. Its differentiation is:

- Skill lifecycle as the primary domain model;
- cross-source evidence reconstruction;
- explicit evidence grading;
- diagnosis at discovery, activation, loading, execution, and outcome boundaries;
- a path from execution attribution to controlled effect evaluation;
- a low-intrusion, local-first experience.

## 10. Product success

The product succeeds when a new user can install or run it against existing local sessions and answer, within five minutes:

1. Which Skills were available?
2. Which Skill ran?
3. What did it load and do?
4. What did it produce?
5. Where is the first missing or failed step?
6. Which conclusions are facts, derivations, or hypotheses?

