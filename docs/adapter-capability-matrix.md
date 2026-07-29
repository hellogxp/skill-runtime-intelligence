# Adapter capability matrix

Status: implemented baseline

## Codex transcript adapter

Adapter version: `0.2.0`

This matrix records what the current adapter can establish from observed local
records. An unsupported signal remains absent; it is never silently inferred.

| Lifecycle signal | Current support | Evidence basis |
|---|---|---|
| Session identity and project | Observed | `session_meta` |
| Turn start and completion | Observed | `task_started`, `task_complete` |
| User request | Observed, redacted summary persisted | `user_message` |
| Tool start and completion | Observed | function/custom tool call records |
| Tool parent/completion relationship | Derived from source call ID | matching `call_id` |
| Explicit Skill invocation | Observed when a `Skill` tool record exists | tool name and input |
| `SKILL.md` loading | Observed | exact Skill file path in tool input |
| Other Skill resource access | Observed at Skill-directory scope | exact directory path in tool input |
| Skill activation from instruction loading | Unsupported | loading does not prove activation mode |
| Candidate Skill matching | Unsupported | current source does not expose candidates |
| Files and artifacts | Partial | exact `Write`/`Edit`/`Create`/`ApplyPatch` and `patch_apply_end.changes` paths; contents omitted |
| Subagents | Unsupported in baseline | planned source-event mapping |
| Token and cost totals | Unsupported in baseline | source schema investigation pending |
| Outcome verification | Unsupported | agent completion is only a reported outcome |

## Privacy behavior

- Source transcripts are read only.
- The index stores record hashes, source locators, record kinds, and redacted
  envelopes; it does not duplicate full raw messages or tool payloads.
- Normalized request and outcome summaries pass through common-secret
  redaction and are length-limited.
- The web server binds to `127.0.0.1` by default.

## Known limitations

- Shell commands can encode file access in forms that do not contain an exact
  absolute path. Those accesses are reported as not observed.
- A currently active JSONL file is labeled incomplete until its open turn has a
  matching completion record.
- The source format is not a public stability contract. Sanitized fixtures and
  the adapter version must be updated together when it changes.

## Skill scope attribution

The adapter creates one SkillRun per `(session, turn, Skill)` rather than one
per agent session. An exact Skill path or explicit invocation opens the Skill
scope. Subsequent tool events in the same turn are connected to that SkillRun
with a Derived `skill_scope` relationship. The source tool event remains
Observed; its Skill attribution has an independent evidence grade.

Request and outcome events in the same turn are connected as Derived
`runtime_context`. They are not presented as actions caused by the Skill.

## Codex hook adapter

Adapter version: `0.1.0`
Collection mode: `official_hook`

The Hook Manager is opt-in. `skill-runtime setup` only presents the plan;
`--enable-codex-hooks` is required to change Codex configuration.

| Hook signal | Normalized evidence | Limits |
|---|---|---|
| `SessionStart` / `SessionEnd` | Session boundary | Observed when source session ID exists |
| `UserPromptSubmit` / `Stop` | Turn boundary | Prompt content is not persisted |
| `PreToolUse` / `PostToolUse` | Tool start/completion | Full tool input/output is omitted |
| `PostToolUseFailure` | Tool failure | Error is redacted and capped |
| `Skill` tool at `PreToolUse` | `skill.activated` | Explicit-tool activation only |
| `Skill` tool completion/failure | Activation terminal event | Requires Skill name in hook payload |

Delivery behavior:

- while the runtime is active, a mode-`0600` Unix socket is the primary path;
- installation builds a tiny native sender when a compiler is available;
- across eight balanced local transport runs, the shell/native path delivered
  640/640 events; pooled p50/p95/p99/max were 45.1/78.6/128.4/204.8 ms; 7/8
  latency gates passed while all eight integrity gates passed;
- a fresh binary incurred a 532.3 ms median first direct trial across eight
  runs; installation now prewarms it once, with two local mechanism runs and
  two packaged lifecycle runs preserving the unchanged transport gates;
- the compatible Linux/OpenBSD-`nc` fallback delivered 80/80 events across two
  digest-pinned container runs, with p50 2.0–2.8 ms and p95 6.0–6.1 ms; this
  is fallback evidence and is not pooled with native-sender measurements;
- when the socket is absent, the standalone path attempts bounded HTTP and
  appends a redacted envelope to a mode-`0600` local JSONL queue;
- Hook exit remains successful, so collection cannot block the Agent;
- `skill-runtime start` replays queued events idempotently;
- Hook installation preserves existing groups and writes a timestamped backup;
- removal matches the Skill Runtime management marker and leaves unrelated
  hooks untouched.

Hook and transcript sessions retain separate source identities and share a
correlation key. This prevents a fallback transcript re-index from overwriting
stronger Hook evidence. Cross-source event merging remains a reconstruction
concern, not a storage-side overwrite.

## Claude Code hook adapter

Adapter version: `0.1.0`
Collection mode: `official_hook`

| Hook signal | Normalized evidence | Limits |
|---|---|---|
| `SessionStart` / `SessionEnd` | Session boundary | Observed when source session ID exists |
| `UserPromptSubmit` / `Stop` | Turn boundary | Prompt content omitted |
| `Skill` tool | Explicit activation and terminal event | Observed |
| `UserPromptExpansion` slash command | Slash-command activation | Observed when command name exists |
| `InstructionsLoaded` | Instruction/resource load | Partial; only exact Skill paths are scoped |
| `PreToolUse` / terminal tool hooks | Tool execution and failure | Observed; payload minimized |
| `SubagentStart` / `SubagentStop` | Subagent execution | Observed when emitted |
| `FileChanged` | Exact artifact path | Supported by adapter, not globally installed because watch paths are literal |

Claude hooks are configured with the Agent's asynchronous flag as well as
fail-open collection. No Claude binary or commercial Agent is required to run
the local fixture evaluation; real cross-Agent claims remain pending until an
authenticated second Agent corpus is available.
