# Live same-Skill Agent experiment

The fixture contains one versioned project Skill with a deterministic script
and reference file. Each Agent receives the same task in an isolated
workspace. A trial passes only when:

- the final JSON exactly matches direct script execution;
- the Agent run leaves the task-owned fixture inputs unchanged;
- the runtime evidence shows the Skill instructions and bundled script path;
- source, normalized, and inferred records remain separate.

Pilot runs establish harness feasibility. Paper estimates require repeated
trials with pinned Agent/model versions and paired bootstrap intervals.

## Cross-Agent installed-CLI pilot

Run the same deterministic Skill task through the locally installed Codex,
OpenCode, and Qoder CLIs in isolated workspaces:

```bash
PYTHONPATH=src python3 experiments/live_agent/run_cross_agent_cli_trials.py \
  --database .sri/panorama.db \
  --trials 4
```

This is a black-box installed-system pilot. It intentionally does not claim to
isolate model quality from Agent scaffolding, and it does not download or
proxy a common model. Each Agent receives the same task and byte-identical
Skill, while a deterministic script supplies the outcome check. Agent-owned
runtime metadata changes are recorded separately from task-input mutation.
Qoder trials require `qodercli status` to report an authenticated account;
otherwise they are recorded as `precondition_failed`, not as model failures.
An authenticated pinned binary can be selected without modifying the user's
global CLI link:

```bash
SRI_QODERCLI=/absolute/path/to/qodercli-0.1.26 \
  PYTHONPATH=src python3 experiments/live_agent/run_cross_agent_cli_trials.py \
  --database .sri/panorama.db --agents qoder --trials 4
```

## OpenCode attempt-correlation pilot

Run a project-local official-hook pilot without changing the user's global
OpenCode plugin:

```bash
PYTHONPATH=src python3 \
  experiments/live_agent/run_opencode_attempt_correlation_pilot.py \
  --trials 4 \
  --model opencode/deepseek-v4-flash-free
```

The raw scope-specific token exists only in the parent process environment and
plugin memory, then is deleted before model-requested child processes start.
The temporary evidence stream stores only its digest and the source session
identity. The report retains aggregate evidence and hashed identities only.

Run the randomized blocked token-on/off non-interference experiment:

```bash
PYTHONPATH=src python3 \
  experiments/live_agent/run_opencode_correlation_ablation.py \
  --pairs 8 \
  --seed 20260731 \
  --database .sri/panorama.db
```

Both conditions load the same plugin; only token supply changes. Each block
randomizes on/off order. The functional gate covers outcome preservation,
workload preservation, on-condition correlation, off-condition silence, and
raw-token persistence. Latency differences are reported descriptively and are
not part of the pass gate.

## Balanced failure/outcome and catalog-factor experiments

Run externally nonce-verified success and real non-zero process failures
through all installed Agent CLIs:

```bash
PYTHONPATH=src:. python3 \
  experiments/live_agent/run_cross_agent_failure_outcome_trials.py \
  --database .sri/panorama.db --trials-per-agent 20 --workers 12
```

The report matches collected sessions by hashed source-session identity. A
verified process failure is kept separate from an explicit normalized failure
event. Controlled failures are not relabeled as production incidents.

Run the randomized balanced 2×2×2×2 Codex catalog study:

```bash
PYTHONPATH=src:. python3 \
  experiments/live_agent/run_catalog_factorial.py \
  --blocks 3 --workers 8 --seed 20260801
```

The factors are cardinality, description length, semantic overlap, and
flat/progressive instruction disclosure. Selection, reference uptake, hidden
outcome verification, distractor-body reads, and workspace integrity remain
separate endpoints. Marginal contrasts are descriptive for this fixture.
