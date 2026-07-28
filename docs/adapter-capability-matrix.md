# Adapter capability matrix

Status: implemented baseline
Adapter: Codex JSONL
Adapter version: `0.1.0`

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
| Files and artifacts | Unsupported in baseline | planned exact-path attribution |
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
