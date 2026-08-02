# Adapter capability matrix

Status: implemented baseline

## Codex transcript adapter

Adapter version: `0.3.0`

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
- Each transcript path has a separate internal storage identity. Repeated
  upstream session IDs are retained as `source_session_id` and correlated
  without overwriting another transcript.
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

Adapter version: `0.3.0`
Collection mode: `official_hook`

The Hook Manager is opt-in. `skill-runtime setup` only presents the plan;
`--enable-codex-hooks` is required to change Codex configuration.

| Hook signal | Normalized evidence | Limits |
|---|---|---|
| `SessionStart` / `SessionEnd` | Session boundary | Observed when source session ID exists |
| `UserPromptSubmit` / `Stop` | Turn boundary | Prompt content is not persisted |
| `PreToolUse` / `PostToolUse` | Tool start/completion | Full tool input/output is omitted |
| Successful tool access to exact `SKILL.md` path | `instruction.loaded` and SkillRun scope | Derived from an Observed successful tool event; raw command omitted |
| Successful access to `scripts/`, `references/`, or `assets/` | `resource.executed` / `resource.read` | Exact standard resource path only; raw input omitted |
| Successful structured write/edit or `apply_patch` | File/artifact path | Exact changed paths only; patch content omitted |
| `PostToolUseFailure` | Tool failure | Error is redacted and capped |
| `Skill` tool at `PreToolUse` | `skill.activated` | Explicit-tool activation only |
| `Skill` tool completion/failure | Activation terminal event | Requires Skill name in hook payload |
| Typed Skill selection on `UserPromptSubmit` | request plus `skill.activated` | Observed only when the Hook payload exposes an exact structured identity; prompt text is never classified |

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

Adapter version: `0.3.0`
Collection mode: `official_hook`

| Hook signal | Normalized evidence | Limits |
|---|---|---|
| `SessionStart` / `SessionEnd` | Session boundary | Observed when source session ID exists |
| `UserPromptSubmit` / `Stop` | Turn boundary | Prompt content omitted |
| `Skill` tool | Explicit activation and terminal event | Observed |
| `UserPromptExpansion` slash command | Slash-command activation | Observed when command name exists |
| Typed Skill selection on `UserPromptSubmit` | UI-selection activation | Observed only when an exact structured Skill field/attachment is emitted |
| `InstructionsLoaded` | Instruction/resource load | Partial; only exact Skill paths are scoped |
| `PreToolUse` / terminal tool hooks | Tool execution and failure | Observed; payload minimized |
| `SubagentStart` / `SubagentStop` | Subagent execution | Observed when emitted |
| `FileChanged` | Exact artifact path | Supported by adapter, not globally installed because watch paths are literal |

Claude hooks are configured with the Agent's asynchronous flag as well as
fail-open collection. No Claude binary or commercial Agent is required to run
the local fixture evaluation; real cross-Agent claims remain pending until an
authenticated second Agent corpus is available.

## Qoder hook adapter

Adapter version: `0.3.0`

Collection mode: `official_hook`

Qoder is integrated through its documented
[command Hook interface](https://docs.qoder.com/extensions/hooks).
Installation is opt-in and additive: existing groups in
`~/.qoder/settings.json` are preserved, a timestamped backup is created, and
only entries carrying the Skill Runtime management marker are removed on
uninstall.

| Hook signal | Normalized evidence | Limits |
|---|---|---|
| `UserPromptSubmit` / `Stop` | Turn boundary | Prompt and response content omitted |
| `PreToolUse` / `PostToolUse` | Tool start/completion | Inputs are minimized before persistence |
| `PostToolUseFailure` | Tool failure | Redacted, capped error summary only |
| `Skill` at `PreToolUse` | Explicit `skill.activated` event | Depends on Qoder exposing the Skill as a tool |
| UI Skill chip / slash context | `skill.activated` plus exact turn identity | Observed from Qoder's bounded `session_meta/slash_command` Skill record; only name, `SKILL.md` path, timestamp, and record/turn IDs are retained |

Qoder command Hooks are synchronous at the Agent boundary, so every generated
command is fail-open (`|| true`) and uses the bounded native sender. A sender or
Collector failure therefore loses or queues telemetry rather than delaying or
denying the Agent action. Qoder must be restarted after the configuration is
installed.

Qoder currently serializes its UI Skill chip through the same structured
`slash_command` record used for Skill context injection, so the normalized
entrypoint is `slash_command`; SRI does not relabel that source fact as an
explicit tool call. The transcript tail read is bounded and excludes messages,
tool content, and responses.

The adapter does not claim candidate discovery, model-internal selection
reasons, or semantic effectiveness. Qoder Skills are discovered read-only from
the [documented user and project Skill directories](https://docs.qoder.com/extensions/skills).

## OpenCode plugin adapter

Adapter version: `0.3.0`

Collection mode: `official_hook`

OpenCode is integrated through a managed, observation-only global plugin at
`~/.config/opencode/plugins/skill-runtime-intelligence.js`. The plugin uses
[documented public callbacks](https://opencode.ai/docs/plugins/) and starts a
detached sender without awaiting delivery. It does not register model-parameter,
system-prompt, permission, or authentication callbacks.

| OpenCode callback/event | Normalized evidence | Limits |
|---|---|---|
| `session.created` / `session.idle` | Session start and turn completion | Idle is not a semantic success verdict |
| `session.error` | Failed turn boundary | Provider error content is redacted and capped |
| `chat.message` | User request boundary | Message text and parts are intentionally omitted |
| Typed Skill part/attachment on `chat.message` | request plus Skill activation | Only exact structured Skill identity/path is forwarded; message content is omitted |
| `tool.execute.before` / `tool.execute.after` | Tool start/completion | Tool output is intentionally omitted |
| `skill` tool before/after | Explicit activation and terminal event | Requires the OpenCode Skill tool callback |

The exact managed file is never overwritten or removed unless it contains the
Skill Runtime ownership marker. The plugin first starts the native sender and
falls back once to the Python CLI sender if process startup or delivery fails;
all integration exceptions are swallowed so OpenCode execution remains
fail-open. OpenCode must be restarted if it was already running during
installation.

OpenCode Skill discovery covers its standard global and project directories,
plus the shared `.agents/skills` compatibility location. Custom directories
declared by third-party plugins are not yet automatically discovered and remain
an explicit adapter limitation.

## Activation entrypoint summary

| Agent | Skill tool | UI / typed context | Slash / Skill message | Exact `SKILL.md` evidence |
|---|---|---|---|---|
| Codex | Observed when emitted | Partial; exact structured Hook field only | Partial; source/version dependent | Observed/Derived from exact path |
| Claude Code | Observed | Partial; exact structured Hook field only | Observed through `UserPromptExpansion` | Partial through `InstructionsLoaded` or exact path |
| Qoder | Observed when emitted | Observed through structured local `slash_command` metadata | Observed through the same Qoder metadata contract | Derived from exact path |
| OpenCode | Observed through stable `skill` tool | Partial; typed part/attachment only | Partial; typed Skill message only | Derived from exact path |

For all four adapters, the runtime event remains Observed while the
relationship that associates later tool/file events with the persisted active
Skill scope is Derived. Missing structured metadata remains Not observed or
Unsupported; SRI never guesses activation from the user's wording.

## Cross-Agent support boundary

The four adapters normalize into the same evidence schema, but they do not
pretend to have identical source capabilities. Agent name, adapter version,
collection mode, raw source identity, normalized evidence, and attribution
relationships remain independently recorded. Cross-Agent comparison is
therefore comparison over graded evidence—not proof that every Agent exposed
the same hidden lifecycle.
