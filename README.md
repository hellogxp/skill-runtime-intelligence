# Agent Skill Runtime Intelligence

> See how every Agent Skill is discovered, activated, executed, and connected to its observable results.

Agent Skill Runtime Intelligence is a local-first, read-only developer tool for understanding Agent Skill runs. It combines Skill files, agent runtime events, session transcripts, and workspace outcomes into an evidence-graded execution panorama.

This repository uses a descriptive working title. A final open-source product name will be selected after repository, package, domain, and trademark checks.

## The problem

Installing a Skill does not prove that an agent discovered it. Discovery does not prove activation. Activation does not prove that the full instructions and resources were loaded. Execution does not prove that the Skill improved the outcome.

Today, these failures are often silent. Developers are left asking:

- Was the Skill available to this agent?
- Did it activate for this request?
- Which instructions, references, scripts, and assets were loaded?
- Which tools, MCP calls, subagents, files, and artifacts were involved?
- Where did the run fail, retry, or lose context?
- Did the Skill help, or did it only add cost and latency?

## Product direction

The first product is a **Skill Run Panorama**:

```text
User request
    ↓
Skills discovered
    ↓
Skill selected / not selected
    ↓
SKILL.md activated
    ↓
References and scripts loaded
    ↓
Tools / MCP / subagents executed
    ↓
Files and artifacts produced
    ↓
Observable outcome
```

The panorama is built from real signals, not model self-report:

| Source | Examples | Evidence |
|---|---|---|
| Skill files | metadata, instructions, scripts, references, assets | Observed |
| Runtime events | Skill calls, tool calls, subagents, failures, duration | Observed |
| Session transcripts | prompts, messages, tool inputs and outputs, ordering | Observed |
| Workspace outcomes | file changes, Git diff, reports, generated artifacts | Observed |
| Correlation | relationships between events, resources, and outcomes | Derived or Inferred |

## Evidence discipline

The UI must never present an inference as a runtime fact:

- **Observed** — explicitly present in a source event or file.
- **Derived** — deterministically connected from observed evidence.
- **Inferred** — a plausible explanation with uncertainty.
- **Experimental** — an effect measured through controlled paired evaluation.

A single trace can support execution attribution. It cannot prove causal effectiveness. Claims such as “this Skill improved success rate” require repeated with-Skill/without-Skill evaluation.

## Product principles

- Local-first and private by default.
- Read-only observation; never take over the agent loop.
- No model proxy and no mandatory cloud service.
- No blocking, approval gate, or policy enforcement in the default product.
- Explicit provenance and evidence grading.
- Progressive disclosure: simple narrative first, raw events on demand.
- Adapter-based support for changing agent transcript formats.

## Initial scope

The MVP supports Claude Code and Codex and provides:

- installed Skill discovery and validation;
- session import and live local observation where supported;
- Skill activation, resource loading, and tool-call timelines;
- subagent, MCP, file, and artifact relationships;
- duration, token, error, retry, and status summaries when available;
- a runs list, panorama DAG, event timeline, and node inspector.

The MVP does **not** include a marketplace, universal agent runtime, security enforcement, enterprise governance, or causal-effect claims.

## Try the SkillRun-first runtime

The baseline implementation has no runtime dependencies beyond Python 3.9+.
From the repository root:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence dev
```

Then open [http://127.0.0.1:4317](http://127.0.0.1:4317).

An optional offline editable install also works with the macOS system Python:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-panorama dev
```

This command:

1. scans user, project, and cached-plugin Skill locations;
2. reads existing Codex JSONL sessions without modifying them;
3. writes a local SQLite index to `.sri/panorama.db`;
4. reconstructs independent SkillRuns and their evidence relationships;
5. serves the SkillRun list, lifecycle panorama, timeline, and attribution inspector.

To index and serve separately:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence index
PYTHONPATH=src python3 -m skill_runtime_intelligence serve
```

Import an existing trace export from a mainstream observability system:

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

The versioned import profiles currently recognize OTLP/Phoenix, Langfuse,
LangSmith, W&B Weave, and Datadog JSON shapes. They only create a SkillRun when
the source carries explicit Skill semantics; generic span names are not treated
as activation evidence.

The server binds to `127.0.0.1` by default. Full transcript messages and tool
payloads are not copied into the index. Common secret patterns are redacted
before normalized summaries are persisted.

Run the dependency-free test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Documentation

- [Product definition](docs/product-definition.md)
- [MVP specification](docs/mvp-specification.md)
- [Runtime event model](docs/runtime-event-model.md)
- [UI information architecture](docs/ui-information-architecture.md)
- [Adapter capability matrix](docs/adapter-capability-matrix.md)
- [Observability interoperability](docs/observability-interoperability.md)
- [Research and competitive landscape](docs/research-and-competitive-landscape.md)
- [Research paper agenda](docs/research-paper-agenda.md)

## Roadmap

1. **v0.1 — Run panorama:** accurately reconstruct what a Skill did.
2. **v0.2 — Diagnosis and comparison:** explain missing activation, conflicts, and differences between runs or versions.
3. **v0.3 — Effect evaluation:** controlled with-Skill/without-Skill paired evaluation.

## Project status

A SkillRun-first Codex runtime is runnable: Skill discovery, passive session
indexing, active-scope attribution, exact patch artifact evidence, redaction,
separate source/relationship evidence, SQLite storage, a local API, and the
Skill Runtime Panorama UI. A vendor-neutral JSON import layer supports
OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, and Datadog profiles. Claude Code
ingestion, richer non-patch artifact attribution, live local hooks, and
controlled evaluation remain planned work.
