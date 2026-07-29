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

Install the latest standalone release on macOS or Linux:

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

No clone, GitHub account, `sudo`, or GitHub CLI is required. The installer
downloads the matching signed-release payload, verifies SHA-256 checksums,
asks once before enabling fail-open Agent hooks, and stores all runtime data
under `~/.skill-runtime`. It then starts the local runtime and opens
[http://127.0.0.1:4317](http://127.0.0.1:4317).

You can [inspect the installer](scripts/install.sh) before running it.

Or run directly from a source checkout:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Open [http://127.0.0.1:4317](http://127.0.0.1:4317). For Codex, review and
trust the managed commands in `/hooks`, start one new Agent turn, then verify:

```bash
skill-runtime doctor
```

The integration becomes **Verified** only after a real official-hook event is
received. A configured hook is shown as **Pending**, never as live evidence.

| Product surface | What it answers |
|---|---|
| Runtime Overview | Which SkillRuns need attention? |
| First Observable Boundary | Where did evidence first become missing or failed? |
| Skill Run Panorama | How did request, activation, resources, tools, artifacts, and outcome connect? |
| Evidence Inspector | What source, grade, basis, and adapter capability support this claim? |
| Compare | Is a difference behavioral, or only an observability difference? |
| Settings / Doctor | What is read, stored, exported, pending, and verified? |

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

- Private by default, with local, hybrid, and team-connected deployment.
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

## Detailed installation

The baseline implementation has no runtime dependencies beyond Python 3.9+.
From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/skill-runtime install --enable-hooks
.venv/bin/skill-runtime start
```

Then open [http://127.0.0.1:4317](http://127.0.0.1:4317).

The one-time `install` command:

1. scans user, project, and cached-plugin Skill locations;
2. detects Codex and Claude Code without changing their configuration;
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
added outside managed enterprise configuration. Start a new Agent turn, then
run:

```bash
.venv/bin/skill-runtime doctor
```

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

- [Product definition](docs/product-definition.md)
- [MVP specification](docs/mvp-specification.md)
- [Runtime event model](docs/runtime-event-model.md)
- [UI information architecture](docs/ui-information-architecture.md)
- [Adapter capability matrix](docs/adapter-capability-matrix.md)
- [Observability interoperability](docs/observability-interoperability.md)
- [Observability platform setup](docs/observability-platform-setup.md)
- [Research and competitive landscape](docs/research-and-competitive-landscape.md)
- [Research paper agenda](docs/research-paper-agenda.md)
- [Experiment-driven product philosophy](docs/experiment-driven-product-philosophy.md)
- [Experiment results](docs/experiment-results-2026-07-29.md)
- [PAI-DSW experiment plan](docs/pai-dsw-experiment-plan.md)

## Roadmap

1. **v0.1 — Runtime evidence and diagnosis:** live collection, Skill Run
   Panorama, first-boundary diagnosis, evidence inspection, comparison, and
   OTLP interoperability.
2. **v0.2 — Adapter breadth and diagnosis studies:** additional Agents, real
   cross-Agent experiments, and participant evaluation.
3. **v0.3 — Effect evaluation:** controlled with-Skill/without-Skill paired
   evaluation, kept separate from single-run diagnosis.

## Project status

A SkillRun-first runtime is runnable: installed-definition inventory, Codex
transcript fallback, consent-driven Codex and Claude Code official-hook
adapters, active-scope attribution, exact file/artifact paths, redaction,
separate source/relationship/inference layers, SQLite storage, retention,
cross-run and cross-Agent comparison, deterministic diagnosis, and the live
Panorama UI. OTLP/Phoenix, Langfuse, LangSmith, W&B Weave, and Datadog exports
can be imported; normalized evidence can be exported live through opt-in
OTLP/HTTP. The current reproducible suite has seven passing experiment gates.
Candidate discovery, model-internal selection reasons, semantic effectiveness,
and causal outcome claims remain explicitly unsupported.
