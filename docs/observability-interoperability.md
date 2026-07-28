# Observability interoperability

Status: implemented foundation  
Adapter family version: `0.1.0`  
Snapshot date: 2026-07-28

## Product boundary

Skill Runtime Intelligence is not a replacement for an LLM or agent
observability platform. Those platforms provide traces, spans, calls, sessions,
metrics, and evaluations. This product consumes those signals and reconstructs
a different primary entity:

```text
Vendor trace / local hook / transcript / workspace evidence
                         ↓
             normalized runtime events
                         ↓
                    SkillRun
                         ↓
        lifecycle + evidence graph + diagnosis
```

Agent sessions remain context. A SkillRun is the unit users select, inspect,
compare, and eventually evaluate.

## Canonical interchange layer

OpenTelemetry spans are the canonical interchange representation. The importer
accepts OTLP JSON and vendor JSON exports through versioned profiles:

| Profile | Imported primitive | Current path |
|---|---|---|
| OpenTelemetry | resource spans and spans | Native OTLP JSON |
| Phoenix | OpenInference spans over OTLP | OTLP-compatible profile |
| Langfuse | observations grouped by trace | JSON observation profile |
| LangSmith | runs grouped by trace | JSON run profile |
| W&B Weave | calls grouped by trace | JSON call profile |
| Datadog | LLM Observability spans | JSON span profile |

The shared trace/span/session structure is not the product's domain model. It
is an input substrate.

## Explicit Skill semantic extension

There is no stable cross-vendor semantic convention for Agent Skills. The
importer therefore recognizes explicit attributes only:

```text
skill.runtime.name     preferred product-neutral extension
sri.skill.name         legacy/local alias
gen_ai.skill.name
agent.skill.name
skill.name
skill_name
related_skill_name
skill
```

`skill.runtime.event` and `skill.runtime.stage` may be used to carry a precise
normalized lifecycle event.

The importer does **not** create a SkillRun because a generic span name happens
to resemble a Skill. A span with an explicit Skill attribute is Observed.
Descendant spans inherit that Skill scope as a Derived relationship through
the parent chain.

## Why not use Session as the primary entity

Mainstream systems use several related groupings:

- Langfuse: observations → traces → sessions;
- LangSmith: runs → traces → threads;
- Phoenix/OpenInference: spans → traces → projects/sessions;
- Weave: calls → traces → threads;
- Datadog: spans → traces.

These structures answer “what did this request or agent do?” They do not answer
the Skill-specific boundaries:

1. Was the Skill available?
2. Was it activated?
3. Were its instructions loaded?
4. Which resources were loaded or executed?
5. Which runtime actions occurred in its active scope?
6. Which artifacts and outcomes can be connected by evidence?

One agent session can contain no SkillRuns, one SkillRun, repeated runs of one
Skill, or multiple Skills. The database therefore permits multiple SkillRuns
per session and per Skill.

## Evidence and attribution are separate

For every event, the UI distinguishes:

- **Source fact:** the event's evidence grade, basis, source locator, and
  redacted payload.
- **Skill attribution:** the relationship type, evidence grade, confidence,
  and basis connecting the event to a SkillRun.

An observed tool call can have a derived Skill relationship. An observed
request can be derived runtime context rather than an action caused by the
Skill. This separation is required for calibrated diagnosis.

## Import usage

```bash
PYTHONPATH=src python3 -m skill_runtime_intelligence import \
  ./trace-export.json \
  --format auto
```

Supported values are `auto`, `otel`, `phoenix`, `langfuse`, `langsmith`,
`weave`, and `datadog`.

Imports are local and idempotent at the source trace level. The database stores
a digest and import metadata. Full inputs and outputs are not copied into the
normalized layer.

## Optional exporters

Remote reporting is a secondary adapter boundary:

```text
Skill Runtime database
      ├── local UI
      ├── OTLP exporter (planned)
      ├── rapid-dashboard exporter (planned)
      └── research dataset exporter (explicit opt-in, planned)
```

An exporter must never become required for local reconstruction. It must keep
evidence grades, stable source IDs, and privacy policy intact. `rapid-tele` is
the preferred transport for a future rapid-dashboard adapter because it
already owns hook installation, durable queuing, retry, and delivery.

## Research basis

The interoperability model follows current official concepts:

- OpenTelemetry semantic conventions provide shared span names, kinds, and
  attributes, including evolving GenAI conventions.
- Langfuse models individual observations inside traces and optionally groups
  traces into sessions.
- LangSmith models each unit of work as a run/span, groups runs into traces,
  and groups traces into threads.
- Phoenix receives OpenInference spans using OTLP and distinguishes agent,
  tool, retriever, reranker, LLM, embedding, and chain span kinds.
- W&B Weave models executions as Calls, nested into trace trees and optionally
  grouped into threads.
- Datadog Agent Observability models agent/workflow/LLM/tool/task/retrieval/
  embedding spans and supports querying and exporting span records.

These systems validate trace/span interoperability, but none removes the need
for a Skill-specific lifecycle and evidence-attribution layer.
