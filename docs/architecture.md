# Architecture

Agent Skill Runtime Intelligence is a sidecar-style evidence and diagnosis
system. It observes supported Agents without becoming their task entrypoint,
model proxy, orchestrator, or policy gate.

![Runtime architecture](assets/runtime-architecture.svg)

## Design goals

1. Make `SkillRun` the primary diagnostic entity; keep Agent sessions as
   context.
2. Prefer official Agent telemetry and observation APIs.
3. Degrade to explicitly labeled fallbacks instead of inventing certainty.
4. Preserve source truth separately from normalization and analysis.
5. Keep collection read-only, local by default, and fail-open.
6. Export through standard observability protocols without weakening
   Skill-specific semantics.

## Data path

```text
Agent-native events ──┐
Skill definitions ────┼─→ Versioned adapter ─→ Local Collector
Workspace outcomes ───┤          │                    │
Session fallback ─────┘          └─ redact/minimize ──┤
                                                      ▼
                                           Source evidence store
                                                      │
                                                      ▼
                                        Normalized lifecycle events
                                                      │
                                  ┌───────────────────┼───────────────────┐
                                  ▼                   ▼                   ▼
                           Relationships        Deterministic        Inferred
                                                diagnosis            analysis
                                  └───────────────────┼───────────────────┘
                                                      ▼
                                  Local UI / REST / SSE / optional OTLP export
```

## Collection layer

### Primary adapters

Each Agent integration is versioned independently because event names,
payloads, lifecycle semantics, and trust mechanisms change at different
speeds. Primary integrations currently cover:

- Codex official command Hooks;
- Claude Code official Hooks;
- Qoder official command Hooks;
- an OpenCode observation-only global plugin.

The adapter converts a bounded source event into the stable runtime event
model. It declares its Agent, adapter version, collection mode, source event
identity, and capability limits. A configured adapter is `Pending` until a
real event is received.

### Fail-open transport

Hook callbacks use a permission-restricted local Unix socket and a low-startup
native sender when available. If the Collector is unavailable, a redacted
event can be appended to the local durable queue. Delivery errors are swallowed
at the observation boundary so they cannot deny or change the Agent action.

The Collector replays queued events with event-ID deduplication after restart.

### Fallback and imports

Session transcripts are compatibility evidence, not the product's primary
telemetry contract. Their source is always labeled `Transcript fallback`.

Historical exports from supported observability products can be imported
through versioned profiles. Generic spans do not become Skill activation
evidence unless the source contains explicit Skill semantics.

## Storage boundaries

The default SQLite database is:

```text
~/.skill-runtime/data/panorama.db
```

The store separates:

| Layer | Contents | Mutation rule |
|---|---|---|
| Source evidence | Redacted source envelope and opaque source locator | Append-only source identity |
| Normalized events | Stable Skill lifecycle vocabulary | Deterministic adapter output |
| Relationships | Parent/child, active-scope, resource, artifact links | Stored separately with basis and grade |
| Findings | First observable boundary and deterministic diagnosis | Recomputable from evidence |
| Inferences | Explanations and suggested investigations | Cannot overwrite other layers |

Raw prompts, full tool payloads, patch bodies, credentials, and Skill resource
contents are not required for the diagnostic index and are discarded or
minimized before persistence.

## Runtime evidence engine

The engine reconstructs this ordered lifecycle:

```text
Request → Discovery → Activation → Instructions
        → Resources → Execution → Artifacts → Outcome
```

It applies four evidence grades:

| Grade | Contract |
|---|---|
| Observed | Direct source fact |
| Derived | Deterministic transformation or relationship from observed facts |
| Inferred | Uncertain explanation bounded by cited evidence and missing signals |
| Experimental | Result of a controlled evaluation, separate from a single run |

An event and its relationship to a SkillRun are different claims. For example,
a tool call may be Observed while its active-scope attribution is Derived.

### Boundary-first diagnosis

The deterministic engine identifies the earliest lifecycle stage at which
evidence becomes missing or failed before later activity. This is a diagnostic
starting point, not a statement that the Skill caused the outcome.

A repeated missing stage across many runs can indicate adapter coverage rather
than repeated Skill failure. Runtime Overview aggregates that pattern and
keeps it separate from run-specific findings.

### Capability-aware comparison

Same-Agent and cross-Agent comparison applies independent comparability masks
to ordered lifecycle behavior, terminal outcome evidence, and absolute time.
Unsupported dimensions remain inspectable side by side but cannot produce a
behavioral difference claim.

## Serving and interoperability

`skill-runtime start` runs:

- the local HTTP Collector at `POST /api/events`;
- a permission-restricted Hook socket;
- incremental fallback watchers;
- queue replay and retention workers;
- SQLite storage;
- REST APIs and the SSE live stream;
- the local diagnostic UI;
- optional, explicitly configured OTLP/HTTP export.

Normalized export omits prompts, raw tool payloads, credentials, and Skill
resource contents. Export destination health and retry checkpoints are visible
in Settings. The interoperability model is detailed in
[Observability interoperability](observability-interoperability.md).

## Trust and failure model

| Condition | Product behavior |
|---|---|
| Runtime is stopped during a Hook callback | Queue minimal redacted evidence or drop safely; never block the Agent |
| Source does not expose activation | Show `Not observed` or `Unsupported`; do not infer activation as fact |
| Adapter cannot verify terminal outcome | Preserve reported outcome separately from verified outcome |
| Export endpoint is unavailable | Retain local checkpoint and retry without affecting local collection |
| Inference service is unavailable | Deterministic reconstruction and diagnosis continue to work |
| Uninstall is requested | Remove only managed entries; keep Agent and Skill sources untouched |

## Related specifications

- [Runtime event model](runtime-event-model.md)
- [Adapter capability matrix](adapter-capability-matrix.md)
- [UI information architecture](ui-information-architecture.md)
- [Observability platform setup](observability-platform-setup.md)
- [Product definition](product-definition.md)
