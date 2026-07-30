# Agent Skill Runtime Intelligence

[![CI](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml/badge.svg)](https://github.com/hellogxp/skill-runtime-intelligence/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/hellogxp/skill-runtime-intelligence)](https://github.com/hellogxp/skill-runtime-intelligence/releases/latest)
[![License](https://img.shields.io/github/license/hellogxp/skill-runtime-intelligence)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB)](https://www.python.org/)

<!-- locale-switcher:start -->
**English** · [简体中文](README.zh-CN.md) · [繁體中文](README.zh-TW.md) ·
[Français](README.fr.md) · [Deutsch](README.de.md) · [Italiano](README.it.md) ·
[Español](README.es.md) · [日本語](README.ja.md) · [한국어](README.ko.md) ·
[Русский](README.ru.md) · [Português (Brasil)](README.pt-BR.md) ·
[Türkçe](README.tr.md) · [Polski](README.pl.md) · [Čeština](README.cs.md) ·
[Magyar](README.hu.md)
<!-- locale-switcher:end -->

> Diagnose where an Agent Skill run first diverged—and inspect the evidence
> behind every conclusion.

Agent Skill Runtime Intelligence is a read-only runtime evidence and diagnosis
system for Agent Skills. It combines Skill definitions, official Agent runtime
events, imported traces, session fallback, and observable workspace outcomes
into an evidence-graded Skill Run Panorama.

![Skill Run Panorama](docs/assets/skill-run-panorama.png)

## Quick start

Install and start the latest release on macOS or Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

No clone, account, `sudo`, or GitHub CLI is required. The installer verifies
the release checksum, detects supported Agents and Skills, explains every path
it will read, asks once before enabling observation-only hooks, and opens the
local UI at [http://127.0.0.1:4317](http://127.0.0.1:4317). Runtime data stays
under `~/.skill-runtime` unless you explicitly configure an export.

You can [inspect the installer](scripts/install.sh) before running it.

### See your first live SkillRun

1. Accept the optional fail-open Hook setup when the installer asks.
2. Restart the Agent and begin a new task. In Codex, review the managed
   commands in `/hooks` first; existing tasks do not hot-load new Hooks.
3. Use a Skill normally, then confirm the integration and open the UI:

```bash
skill-runtime doctor
skill-runtime status
```

An integration is **Live** only after the Collector receives a real runtime
event. A configured but unobserved Hook is **Pending**—never presented as live
evidence. Open [http://127.0.0.1:4317](http://127.0.0.1:4317), or see the
[Getting Started guide](docs/getting-started.md) for Agent-specific
instructions and troubleshooting.

To run directly from a source checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

| Product surface | What it answers |
|---|---|
| Runtime Overview | Which SkillRuns need attention? |
| First Observable Boundary | Where did evidence first become missing or failed? |
| Skill Run Panorama | How did request, activation, resources, tools, artifacts, and outcome connect? |
| Evidence Inspector | What source, grade, basis, and adapter capability support this claim? |
| Compare | Is a difference behavioral, or only an observability difference? |
| Inferred Analysis | What evidence-bounded explanation or next investigation is plausible? |
| Settings / Doctor | What is read, stored, exported, pending, and verified? |

## How it works

![Runtime architecture](docs/assets/runtime-architecture.svg)

Skill Runtime observes the workflow you already use. Versioned adapters turn
Agent-native events into a stable Skill lifecycle, while raw source envelopes,
normalized events, relationships, and inferences remain separate. The
diagnosis engine first identifies the earliest boundary where evidence becomes
missing or failed; it does not invent model intent or causal effectiveness.

| Data source | Role | Freshness | UI label |
|---|---|---|---|
| Official Agent hooks / plugins / SDK events | Primary lifecycle, tool, subagent, and terminal evidence | Live | `Official hook` / `Native telemetry` |
| Skill files and observable workspace outcomes | Definition, resource, file, artifact, and test evidence | Live snapshot / indexed | `Observed` |
| Session transcripts | Compatibility fallback when the Agent exposes no sufficient runtime API | Near-live or historical | `Transcript fallback` |
| OTLP and supported trace exports | Interoperability and historical import | Live export / batch import | Source profile shown |
| Deterministic correlation | Connects events to a SkillRun without changing source facts | At ingestion | `Derived` |
| Semantic assistance | Explanations and investigation suggestions only | On demand | `Inferred` |

Supported first-party adapters are versioned independently:

| Agent | Primary integration | Fallback | Activation visibility |
|---|---|---|---|
| Codex | Official command Hooks | Session import | Explicit activation when exposed by the Hook event |
| Claude Code | Official Hooks | Session import | Explicit Skill tool and slash-command evidence where exposed |
| Qoder | Official command Hooks | Local records | Explicit activation when exposed by its Skill tool |
| OpenCode | Observation-only global plugin | Local records | Skill tool callbacks where exposed |

Exact capability limits are documented in the
[adapter capability matrix](docs/adapter-capability-matrix.md). Unsupported and
not-observed stages stay visible instead of being converted into failures.

## The problem

Installing a Skill does not prove that an agent discovered it. Discovery does not prove activation. Activation does not prove that the full instructions and resources were loaded. Execution does not prove that the Skill improved the outcome.

Today, these failures are often silent. Developers are left asking:

- Was the Skill available to this agent?
- Did it activate for this request?
- Which instructions, references, scripts, and assets were loaded?
- Which tools, MCP calls, subagents, files, and artifacts were involved?
- Where did the run fail, retry, or lose context?
- Did the Skill help, or did it only add cost and latency?

## Skill-specific diagnosis

The primary diagnostic object is a `SkillRun`, not an entire Agent session:

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

The UI keeps the lifecycle ordered, typed, and evidence-graded. Missing
activation telemetry means “not observed” or “unsupported”; it does not mean
the Agent definitely skipped the Skill.

## Evidence discipline

The UI must never present an inference as a runtime fact:

- **Observed** — explicitly present in a source event or file.
- **Derived** — deterministically connected from observed evidence.
- **Inferred** — a plausible explanation with uncertainty.
- **Experimental** — an effect measured through controlled paired evaluation.

A single trace can support execution attribution. It cannot prove causal effectiveness. Claims such as “this Skill improved success rate” require repeated with-Skill/without-Skill evaluation.

## Product principles

- Private by default, with local, hybrid, and team-connected deployment.
- Read-only observation; never take over the agent loop.
- No model proxy and no mandatory cloud service.
- No blocking, approval gate, or policy enforcement in the default product.
- Explicit provenance and evidence grading.
- Progressive disclosure: simple narrative first, raw events on demand.
- Adapter-based support for changing agent transcript formats.

## Current scope

The runtime supports Codex, Claude Code, Qoder, and OpenCode through
independent, versioned adapters and provides:

- installed Skill discovery and validation;
- real-time official Hook/plugin collection plus labeled session fallback;
- Skill activation, resource loading, and tool-call timelines;
- subagent, MCP, file, and artifact relationships;
- duration, token, error, retry, and status summaries when available;
- Runtime Overview and first-boundary diagnosis;
- a panorama DAG, event timeline, and evidence inspector;
- capability-aware same-Agent and cross-Agent comparison;
- a separate Inferred Analysis surface that cannot rewrite runtime facts;
- opt-in OTLP/HTTP export and supported observability-trace import.

The MVP does **not** include a marketplace, universal agent runtime, security enforcement, enterprise governance, or causal-effect claims.

## Detailed installation

For the shortest supported path, use the one-line release installer in
[Quick start](#quick-start). The complete first-run flow, Agent-specific
restart/trust steps, privacy behavior, and troubleshooting live in the
[Getting Started guide](docs/getting-started.md).

For development, the baseline implementation has no runtime dependencies
beyond Python 3.9+. From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Then open [http://127.0.0.1:4317](http://127.0.0.1:4317).

The one-time `install` command:

1. scans user, project, and cached-plugin Skill locations;
2. detects Codex, Claude Code, Qoder, and OpenCode without changing their
   configuration;
3. shows which Agent and Skill paths will be read;
4. downloads a checksum-verified low-startup native sender for the current
   platform, falling back to a local C build and finally the Python sender,
   and prewarms a fresh native binary once during installation;
5. creates `~/.skill-runtime/config.json` and the local SQLite index.

When run interactively, it asks once before adding fail-open Agent hooks.
`--no-hooks` keeps transcript import as the labeled fallback, while
`--enable-hooks` records explicit consent and installs only managed entries.
For Codex, open `/hooks` after installation, review the exact managed commands,
and trust them. Codex intentionally requires this explicit review for hooks
added outside managed enterprise configuration. Start a new Codex task/session
after trusting the Hooks, then run:

```bash
.venv/bin/skill-runtime doctor
```

Qoder loads Hook configuration at startup, so restart Qoder after first
installation. OpenCode discovers the managed observation-only plugin from its
global plugin directory; restart OpenCode if the current process predates
installation. Neither integration reads or changes model requests.

The integration becomes **Live** only after the database receives a real
`official_hook` event. Merely writing `~/.codex/hooks.json` is shown as
**Pending**, never Connected. `start` launches the Collector, transcript
fallback watcher, retention worker, SQLite store, and live UI as a managed
background process. No model request is proxied.

Lifecycle commands:

```bash
skill-runtime status
skill-runtime doctor
skill-runtime restart
skill-runtime stop
skill-runtime config --set retention_days=30
skill-runtime config --set network_export.endpoint=https://collector.example/v1/traces
skill-runtime config --set network_export.enabled=true
skill-runtime uninstall --keep-data
```

`uninstall` removes only managed Hook entries and Skill Runtime-owned files.
Without `--keep-data`, it requires interactive confirmation (or `--yes`) before
removing `~/.skill-runtime`; Agent sessions and Skill sources are never removed.

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

Export normalized, Skill-specific runtime evidence to any OTLP/HTTP traces
endpoint:

```bash
.venv/bin/skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces \
  --otlp-header Authorization='Bearer …'
```

Export is disabled unless an endpoint is explicitly configured. Checkpoints,
retry status, and destination health are shown in Settings. Raw prompts, tool
payloads, credentials, and Skill resource contents are not exported.
For authenticated background export, provide standard
`OTEL_EXPORTER_OTLP_HEADERS` in the environment before `skill-runtime start`;
headers are never written to Skill Runtime configuration or process arguments.

## Send live runtime evidence

`skill-runtime start` includes a local Collector. Native telemetry adapters,
official hooks, lightweight fail-open hooks, and SDK integrations can append a
single event or a bounded batch to `POST /api/events`:

```bash
curl -X POST http://127.0.0.1:4317/api/events \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "evt-example-activation",
    "event_type": "skill.activated",
    "occurred_at": "2026-07-29T05:00:00Z",
    "session_id": "agent-session-example",
    "turn_id": "turn-1",
    "activation_mode": "explicit_tool",
    "skill": {"name": "pdf"},
    "source": {
      "adapter": "example-agent",
      "adapter_version": "1.0",
      "collection_mode": "official_hook",
      "source_event_id": "source-event-1"
    },
    "evidence": {
      "grade": "observed",
      "confidence": 1.0,
      "basis": "Official runtime hook"
    },
    "payload": {"tool_name": "Skill"}
  }'
```

The endpoint redacts common credentials before persistence, deduplicates by
`event_id`, preserves a separate redacted raw envelope, and returns the
resulting `skill_run_ids`. `GET /api/collector/schema` exposes the supported
event vocabulary and collection modes. The UI listens to `/api/stream` using
SSE, with polling only as a reconnect fallback.

The source indicator distinguishes primary runtime evidence from
`Transcript fallback` and imported traces. A Collector endpoint alone does not
claim native telemetry: every producer must declare whether its event came
from native telemetry, an official hook, a lightweight hook, or an SDK.

### Optional Agent hooks

Inspect the exact paths and events first. This command is read-only:

```bash
.venv/bin/skill-runtime setup
```

Hook installation requires an explicit flag:

```bash
.venv/bin/skill-runtime setup --enable-codex-hooks
.venv/bin/skill-runtime setup --enable-claude-hooks
```

The installer backs up the Agent configuration, preserves existing hooks, and
adds only entries carrying a Skill Runtime management marker. The hook adapter
stores minimal lifecycle fields rather than full prompts or tool payloads.
For completed tool calls it extracts only exact `SKILL.md`, standard Skill
resource, and changed-file paths in memory; raw commands, patch bodies, prompts,
and tool outputs are discarded before persistence.
While the runtime is active, a permission-restricted Unix socket is the fast
path; an optional native sender avoids Python startup. When the runtime is not
active, the standalone fail-open path appends redacted evidence to
`~/.skill-runtime/queue/events.jsonl`. `skill-runtime start` replays that queue
with event-ID deduplication.

Codex events use its official Hook API (`SessionStart`, `SessionEnd`,
`UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PreCompact`, `PostCompact`,
`SubagentStart`, `SubagentStop`, and `Stop`). Codex currently executes command
hooks synchronously, so Skill Runtime uses a local Unix socket/native sender
with a bounded timeout. Any delivery failure is swallowed and queued; it never
changes an Agent decision. See the
[official Codex Hook documentation](https://developers.openai.com/codex/config-advanced#hooks).

Remove only the managed entries with:

```bash
.venv/bin/skill-runtime setup --remove-codex-hooks
.venv/bin/skill-runtime setup --remove-claude-hooks
```

The server binds to `127.0.0.1` by default. Full transcript messages and tool
payloads are not copied into the index. Common secret patterns are redacted
before normalized summaries are persisted.

Run the dependency-free test suite with:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## Release engineering

GitHub Actions runs Python 3.9–3.13 tests, JavaScript validation, native sender
compilation, and a real install/start/doctor/stop/uninstall smoke test. A `v*`
tag builds wheel/sdist packages plus checksum-protected Linux and macOS native
senders. The CLI installer downloads the matching release asset, so end users
do not need a compiler.

Run the first product-linked diagnostics experiment:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

It fault-injects lifecycle evidence gaps, explicit failures, incomplete runs,
and unverified outcomes, then evaluates the same deterministic diagnosis
engine used by the API and UI. See the
[PAI-DSW experiment plan](docs/pai-dsw-experiment-plan.md) for the experiment
ladder, non-interference tests, and reproducibility contract.

After building the wheel, run the isolated packaged lifecycle smoke with:

```bash
PYTHONPATH=src python3 experiments/product_lifecycle/run_benchmark.py
```

It installs into a temporary virtual environment and temporary home, exercises
the full local lifecycle without enabling hooks, and verifies project and
Agent configuration non-interference.

## Experiment-driven product design

Product behavior is constrained by the
[experiment-driven product philosophy](docs/experiment-driven-product-philosophy.md):
evidence before conclusions, the first observable boundary before severity,
typed relationships before flat logs, and deterministic reconstruction before
probabilistic assistance.

Current reproducible local evidence includes:

- 7/7 local experiment gates passed;
- 2,400/2,400 Collector events accepted without input/output mutation;
- 14/14 deterministic fault-corpus diagnoses with no unsupported causal claim;
- relational diagnosis representation at 13/14 exact and F1 0.963, while flat
  lifecycle retrieval reached 1/14 exact and F1 0.080;
- 11/11 study-material cases place the earliest observable boundary first.

These results validate mechanisms and representation choices, not deployment
generalization or human benefit. Real second-Agent studies, cross-platform
tail latency, real-fault calibration, and participant diagnosis studies remain
open evidence gaps.

The research direction is also grounded in adjacent primary work:
[SkillsBench](https://arxiv.org/abs/2602.12670) and
[SWE-Skills-Bench](https://arxiv.org/abs/2603.15401) motivate diagnosis because
Skill effects vary and can regress; [Harness-Bench](https://arxiv.org/abs/2605.27922)
motivates capability-aware cross-Agent comparison; and the
[execution provenance survey](https://arxiv.org/abs/2606.04990) motivates typed
evidence relations, trace provenance, and privacy-aware audit infrastructure.

## Documentation

| Start here | Purpose |
|---|---|
| [Getting Started](docs/getting-started.md) | Install, connect an Agent, verify live evidence, and troubleshoot |
| [Architecture](docs/architecture.md) | Collection pipeline, storage boundaries, evidence engine, and trust model |
| [Adapter capability matrix](docs/adapter-capability-matrix.md) | Exact signals and limitations by Agent/version |
| [Observability platform setup](docs/observability-platform-setup.md) | Connect OTLP-compatible platforms and import supported traces |
| [Runtime event model](docs/runtime-event-model.md) | Stable event vocabulary, provenance, relationships, and evidence grades |
| [UI information architecture](docs/ui-information-architecture.md) | Overview, first boundary, Panorama, Inspector, Compare, and Inferred Analysis |

Product and research references: [product definition](docs/product-definition.md),
[MVP specification](docs/mvp-specification.md),
[observability interoperability](docs/observability-interoperability.md),
[experiment-driven product philosophy](docs/experiment-driven-product-philosophy.md),
[experiment results](docs/experiment-results-2026-07-29.md), and the
[research agenda](docs/research-paper-agenda.md).

## Roadmap

1. **v0.2.0 — Available now:** live fail-open collection, four versioned Agent
   adapters, Runtime Overview, first-boundary diagnosis, Panorama, Evidence
   Inspector, capability-aware Compare, Inferred Analysis, and OTLP
   interoperability.
2. **Next — Adapter and diagnosis hardening:** broader Agent/version coverage,
   real-fault calibration, cross-platform tail-latency validation, and
   participant diagnosis studies.
3. **Later — Effect evaluation:** controlled with-Skill/without-Skill paired
   evaluation, kept explicitly separate from single-run diagnosis.

## Project status

Version `v0.2.0` is published. The runtime includes installed-definition
inventory, consent-driven official Hook adapters for Codex, Claude Code, and
Qoder, an observation-only OpenCode plugin, labeled transcript fallback,
active-scope attribution, exact file/artifact paths, redaction, separate
source/relationship/inference layers, SQLite storage, retention, deterministic
diagnosis, live UI, and cross-run/cross-Agent comparison. OTLP/Phoenix,
Langfuse, LangSmith, W&B Weave, and Datadog exports can be imported;
normalized evidence can be exported live through opt-in OTLP/HTTP.

Candidate discovery inside the model, model-internal selection reasons,
semantic effectiveness, and causal outcome claims remain explicitly
unsupported unless a source or controlled experiment provides that evidence.
