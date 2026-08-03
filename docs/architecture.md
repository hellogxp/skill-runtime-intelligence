# Architecture

Agent Skill Runtime Intelligence is a passive, sidecar-style runtime evidence
and diagnosis system. It can run on a developer workstation or as an
authenticated self-hosted remote service. In either placement it observes
supported Agents without becoming their task entrypoint, model proxy,
orchestrator, or policy gate.

![Runtime architecture](assets/runtime-architecture.svg)

## Design goals

1. Make `SkillRun` the primary diagnostic entity; keep Agent sessions as
   context.
2. Prefer official Agent telemetry and observation APIs.
3. Degrade to explicitly labeled fallbacks instead of inventing certainty.
4. Preserve source truth separately from normalization and analysis.
5. Keep collection non-intervening, read-only against observed sources, and
   fail-open.
6. Export through standard observability protocols without weakening
   Skill-specific semantics.
7. Keep deployment placement independent from trace import and export.

## Data path

```text
Agent-native events ──┐
Skill definitions ────┼─→ Versioned adapter ─→ Workstation or self-hosted Collector
Workspace outcomes ───┤          │                    │
Session fallback ─────┘          └─ redact/minimize ──┤
                                                      ▼
                                   Operator-controlled evidence store
                                                      │
                                                      ▼
                                        Normalized lifecycle events
                                                      │
                                  ┌───────────────────┼───────────────────┐
                                  ▼                   ▼                   ▼
                           Relationships       Behavior checks       Inferred
                                               and diagnosis         analysis
                                  └───────────────────┼───────────────────┘
                                                      ▼
                           UI / REST / SSE / optional trace import and OTLP export
```

The observed Agent and source workspace are read-only inputs. SRI still writes
its own evidence database, queue, checkpoints, and settings. In self-hosted
remote mode, source-side delivery crosses only the explicitly configured,
authenticated transport boundary; it is not an observability export.

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

## Storage and deployment boundaries

In workstation mode, the default SQLite database is:

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

In self-hosted remote mode, the same logical separation applies inside the
operator-managed service. Deployment credentials and observability-export
credentials are separate concerns. A remote deployment can operate without an
external observability platform, and a workstation deployment can still import
or export supported traces.

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

### Behavior constraints and concrete activity

The engine extracts only explicit, observable expectations from the current
`SKILL.md`: named resources, tools, output files, and deterministic verification
steps. It does not translate broad advice or subjective quality language into
false pass/fail rules. `behavior_constraints.py` matches those expectations to
runtime evidence, while `activity_summary.py` exposes the concrete instruction,
resource, tool, artifact, and outcome records represented by lifecycle counts.

Each behavior result preserves three separate questions:

1. what the Skill required;
2. what runtime evidence was matched;
3. whether the available adapter signals can evaluate that requirement.

A missing match is therefore `Needs review` or `Not evaluable` unless an
observable event establishes a violation. Agent-reported completion remains
separate from deterministic outcome verification.

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

The runtime service runs:

- an HTTP Collector at `POST /api/events` (loopback by default, authenticated
  when remote mode is explicitly enabled);
- a permission-restricted Hook socket;
- incremental fallback watchers;
- queue replay and retention workers;
- SQLite storage;
- REST APIs and the SSE live stream;
- the diagnostic UI;
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
