# Getting Started

This guide takes a new user from installation to a **verified live SkillRun**.
Skill Runtime observes supported Agents beside their normal workflow; it does
not proxy model requests, replace the Agent UI, or require a cloud account.

The steps below use the default developer-workstation deployment. SRI can also
run as an authenticated self-hosted remote service. Deployment placement is
independent from supported trace import and opt-in OTLP/HTTP export; neither
mode requires a third-party observability platform.

## Requirements

- macOS or Linux;
- Python 3.9 or newer;
- at least one supported Agent: Codex, Claude Code, Qoder, or OpenCode;
- a browser for the local UI.

The public installer does not require `sudo`, GitHub CLI, or a source checkout.

## 1. Install and start

```bash
curl -LsSf https://raw.githubusercontent.com/hellogxp/skill-runtime-intelligence/main/scripts/install.sh | sh -s -- --start
```

This sequence:

1. downloads the GitHub release payload for the current platform;
2. verifies the published checksum;
3. detects supported Agents and scans standard Skill locations;
4. shows every path it intends to read or manage;
5. records explicit consent for observation-only, fail-open integrations;
6. creates `~/.skill-runtime/config.json` and
   `~/.skill-runtime/data/panorama.db`;
7. starts the local Collector and UI.

All stored runtime evidence stays under `~/.skill-runtime` by default.
The first installation imports compatible historical Agent sessions. Its
duration therefore depends on the size of the local history; later runs are
incremental, and `start` serves the UI while the initial refresh continues in
the background.

## 2. Connect your Agent

Accepting Hook setup during installation enables every detected integration.
To inspect the plan without changing any Agent configuration:

```bash
skill-runtime setup
```

To enable only one integration later:

```bash
skill-runtime setup --enable-codex-hooks
skill-runtime setup --enable-claude-hooks
skill-runtime setup --enable-qoder-hooks
skill-runtime setup --enable-opencode-plugin
```

Every managed configuration entry has a Skill Runtime marker. Existing entries
are preserved and a backup is created before a supported configuration file is
changed.

### Codex

1. Run `skill-runtime setup --enable-codex-hooks`.
2. Open `/hooks` in Codex.
3. Review and trust the commands managed by Skill Runtime.
4. Start a new Codex task; already-open tasks do not hot-load new Hooks.

### Claude Code

Enable the managed Hooks, restart Claude Code if it was already running, and
begin a new session.

### Qoder

Enable the managed Hooks and restart Qoder. Qoder loads its Hook configuration
at process startup.

### OpenCode

Enable the managed observation-only plugin and restart OpenCode if its current
process predates installation.

## 3. Produce and verify live evidence

Use a Skill normally in a new Agent task. Then run:

```bash
skill-runtime doctor
```

The integration states have strict meanings:

| State | Meaning |
|---|---|
| `Live` / `Verified` | The local database received a real runtime event from this integration |
| `Pending` | Configuration exists, but no real event has arrived yet |
| `Fallback` | Evidence is being reconstructed from compatible local records |
| `Unsupported` | This Agent/version does not expose the relevant signal |
| `Disabled` | The integration was not enabled |

Writing a Hook configuration is never enough to claim live collection.

Open [http://127.0.0.1:4317](http://127.0.0.1:4317). The Runtime Overview
identifies runs worth investigating; selecting a run opens its ordered
Panorama, Skill Behavior Check, concrete activity inventory, first observable
boundary, evidence timeline, and Inspector.

Start with **Skill Behavior Check** when the Skill definition contains an
explicit, observable instruction such as reading a named resource, invoking a
tool, producing a file, or verifying a result. Each row shows the expectation,
the runtime match, and the supporting evidence. **Needs review** means the
available evidence does not establish compliance; it is not automatically a
failure. Use **What Actually Happened** to inspect the exact resources, tools,
artifacts, and reported outcome behind the summary.

## 4. Understand what is real

Every node and relationship carries an evidence grade:

- **Observed** — directly present in a source event or scanned file;
- **Derived** — deterministically connected from observed evidence;
- **Inferred** — an uncertain explanation that cannot rewrite facts;
- **Experimental** — an effect measured through controlled evaluation.

`Not observed` is not a synonym for `failed`. The adapter capability panel
shows whether a source could have emitted the missing signal.

## 5. Runtime lifecycle

```bash
skill-runtime status
skill-runtime doctor
skill-runtime restart
skill-runtime stop
skill-runtime uninstall --keep-data
```

`uninstall` removes only entries and files owned by Skill Runtime. Without
`--keep-data`, deletion of `~/.skill-runtime` requires explicit confirmation.
Agent sessions, projects, and Skill sources are never removed.

## 6. Privacy and network behavior

- The server binds to `127.0.0.1` by default.
- Self-hosted remote access requires explicit enablement and an authenticated
  HTTPS boundary; it is not enabled by the workstation flow below.
- Prompts, raw tool payloads, patch bodies, credentials, and Skill resource
  contents are not copied into the normalized index.
- Common secret patterns are redacted before persistence.
- Network export is off until an endpoint is explicitly configured.
- Hook delivery is bounded and fail-open: a collection failure does not deny,
  modify, or delay an Agent decision beyond the small configured timeout.
- “Read-only collection” applies to the observed Agent and source workspace;
  SRI writes its own evidence database, checkpoints, and settings.

Review the exact data boundaries in [Architecture](architecture.md) and the
signal limitations in the [adapter capability matrix](adapter-capability-matrix.md).

## 7. Connect an observability platform

Skill Runtime exports normalized Skill-specific evidence over OTLP/HTTP:

```bash
skill-runtime start \
  --otlp-endpoint https://collector.example/v1/traces
```

For authenticated background export, use the standard
`OTEL_EXPORTER_OTLP_HEADERS` environment variable before starting the runtime.
Secrets are not written into Skill Runtime configuration or command history by
the product.

See [Observability platform setup](observability-platform-setup.md) for
Grafana/OpenTelemetry Collector, Datadog, and other OTLP-compatible backends,
plus supported historical import profiles.

## Troubleshooting

### The integration stays Pending

- confirm the Agent was restarted after setup;
- create a new task/session rather than reusing an existing one;
- for Codex, confirm the managed commands are trusted in `/hooks`;
- use a Skill so the Agent actually emits a Skill-relevant event;
- run `skill-runtime status`, then `skill-runtime doctor`.

### The UI shows Transcript fallback

No verified primary event has arrived for that run. The transcript adapter is
serving compatibility evidence and the UI labels it accordingly. Check
`skill-runtime doctor` and the
[adapter capability matrix](adapter-capability-matrix.md).

### Port 4317 is already in use

```bash
skill-runtime stop
skill-runtime start --port 4318
```

Then open [http://127.0.0.1:4318](http://127.0.0.1:4318).

### I do not want Hooks

```bash
skill-runtime install --no-hooks
```

The product remains usable for Skill inventory, supported imports, and labeled
fallback reconstruction, but it will not present those records as primary live
Hook evidence.
