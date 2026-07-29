# Runtime diagnostics benchmark

This experiment checks whether the production diagnosis engine identifies the
first observable lifecycle boundary without upgrading missing evidence into a
claim that a Skill step did not happen.

Run it from the repository root:

```bash
python3 experiments/runtime_diagnostics/run_benchmark.py
```

The runner:

- loads fault-injection cases from `cases.jsonl`;
- calls the same `diagnose_skill_run` function used by the API and UI;
- compares `(finding code, stage, evidence grade)` tuples;
- records precision, recall, F1, exact-match rate, source digest, Git state, and
  the execution environment;
- writes machine-specific reports under `results/`, which Git ignores.

On PAI-DSW, keep results on a persistent mount and identify the instance:

```bash
export SRI_EXPERIMENT_ROOT=/mnt/workspace/sri-experiments
export PAI_DSW_INSTANCE_ID=<instance-id>
python3 experiments/runtime_diagnostics/run_benchmark.py \
  --output "$SRI_EXPERIMENT_ROOT/runtime-diagnostics-smoke.json"
```

The actual persistent path differs across DSW images. Confirm the mounted path
in the active instance before setting `SRI_EXPERIMENT_ROOT`; do not assume that
container-local files survive a restart.
