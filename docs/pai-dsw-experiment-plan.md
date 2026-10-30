# PAI-DSW Experiment Plan

Status: active design  
Date: 2026-07-28

## 1. Purpose

Experiments are part of product development, not a detached benchmark. They
must answer whether the runtime evidence layer reconstructs and diagnoses
Agent Skill behavior accurately, safely, and usefully.

The product remains observational. Experiments may inject faults into prepared
traces or isolated workloads, but the shipped collector does not block,
rewrite, or orchestrate an Agent run.

## 2. Questions and falsifiable hypotheses

| Question | Initial hypothesis | Primary metric |
|---|---|---|
| Can the system reconstruct the Skill lifecycle from heterogeneous signals? | Versioned adapters recover the observable lifecycle without inventing unsupported stages. | event/stage precision and recall |
| Can diagnosis find the first useful boundary? | Evidence-graded rules identify the first missing or failed observable stage. | first-boundary accuracy |
| Does the evidence language remain calibrated? | Missing evidence is labeled as a gap and never presented as proof of non-execution. | unsupported-claim count |
| Is collection non-interfering? | Passive collection adds negligible latency and does not change Agent success. | p50/p95 overhead and outcome delta |
| Does the diagnosis help a user? | Users locate the root observable boundary faster with the panorama than with raw transcripts. | time-to-diagnosis and correctness |
| Are cross-Agent comparisons meaningful? | The same Skill can be compared on normalized lifecycle facts while retaining adapter-specific capability gaps. | paired-field coverage and false equivalence count |

## 3. Experiment ladder

### E0 — Deterministic diagnosis smoke

Use small, reviewed JSONL fixtures with injected lifecycle gaps, explicit
failures, incomplete sources, and unverified outcomes. The evaluator imports
the production diagnosis function.

Gate:

- 100% exact match on the smoke corpus;
- zero unsupported causal claims;
- output includes dataset digest, code revision, dirty state, and environment.

Implementation:
`experiments/runtime_diagnostics/`.

### E1 — Adapter reconstruction corpus

Build a de-identified golden corpus for each versioned Agent adapter:

- explicit Skill activation;
- implicit or unavailable activation signal;
- references/scripts/assets loaded;
- nested tools, MCP calls, subagents, and artifacts;
- retries, failures, compaction, truncation, and interrupted sessions.

Two reviewers label source facts, normalized events, attribution edges, and
unsupported stages separately. Report precision/recall by Agent, adapter
version, lifecycle stage, and evidence grade. Never mix derived edges into the
observed-event score.

### E2 — Live non-interference and overhead

Run paired workloads with collection disabled and enabled. Fix the Agent,
model, Skill version, prompt set, workspace snapshot, and external tool
fixtures. Repeat enough times to expose variance.

Measure:

- task success delta;
- p50/p95 wall-time overhead;
- CPU, memory, disk, and emitted-byte overhead;
- missing and duplicate event rate;
- any changed tool input, output, or Agent control flow.

Fail the experiment if the default collector modifies an Agent action or
becomes a required hop in the model request path.

### E3 — Diagnostic usefulness study

Give participants a balanced set of real failure cases. Compare:

1. raw Agent transcript and files;
2. Skill Run Panorama with evidence-graded findings.

Measure correct first-boundary identification, diagnosis time, confidence
calibration, and false causal conclusions. Capture where the UI lacks evidence
or sends users to the wrong next check.

### E4 — Same Skill across Agents

Run the same versioned Skill and task fixtures on supported Agents. Compare
normalized facts only when both adapters expose equivalent capabilities.
Show unsupported or partial fields explicitly rather than filling them with
inference.

Measure:

- comparable-field coverage;
- lifecycle and resource-loading differences;
- failure-boundary agreement;
- false equivalence and false difference rates.

### E5 — Learned or semantic diagnosis research

Only after E0–E4 provide a trusted evidence substrate, evaluate whether a
model-assisted layer can summarize novel patterns. Its output is Inferred,
must cite source evidence, and is never allowed to overwrite Observed or
Derived records.

PAI-DSW GPU resources may be useful here; E0–E4 should not require a GPU.

## 4. Reproducibility contract

Each result bundle must contain:

- experiment and result schema versions;
- code revision and dirty-worktree flag;
- adapter, Agent, model, and Skill versions where applicable;
- immutable case/trace digest;
- environment fingerprint and DSW instance identifier;
- configuration, seed, timestamps, and raw metric counts;
- per-case output, not only aggregate scores.

Raw source events, normalized events, relationships, and inferred findings
remain separate. Sensitive content is removed or redacted before a corpus is
shared.

## 5. PAI-DSW execution shape

Use a persistent DSW mount for source snapshots and result bundles. Keep large
or sensitive raw traces outside Git; keep small de-identified fixtures and
experiment definitions in this repository.

```text
repository revision
        +
versioned JSONL cases / trace manifest
        ↓
isolated DSW experiment process
        ↓
raw result bundle + environment fingerprint
        ↓
reviewed aggregate metrics and product decisions
```

The active instance must be probed before choosing a path because DSW images
and mounts differ. The runner accepts an explicit output path so the same code
works locally and on the persistent mount.

## 6. First development loop

1. Keep E0 green while diagnosis rules and UI evolve.
2. Add golden traces for the Codex adapter and review false attribution edges.
3. Implement fail-open live collection for an Agent with first-party hooks.
4. Run E2 before calling the collector “non-interfering.”
5. Use failures from E1–E3 to prioritize product work.
6. Start cross-Agent E4 only when both participating adapters declare their
   capability matrices.

The next product milestone is not “more telemetry.” It is a reviewed diagnostic
case where the panorama points to the correct observable boundary, shows the
supporting evidence, admits what is unavailable, and suggests the next check.
