# Multi-repository controlled mechanism benchmark

This final benchmark freezes three tracked files from each of six real Git
repositories at their current commits, overlays one repository-specific
read-only audit Skill per repository, and crosses every Skill with clean plus
six controlled fault conditions. Source repositories are never modified.

The fault manifest and deterministic nonce-bound probe are the gold-label
authority. Agent responses, collected telemetry, normalized SkillRuns, and
model diagnoses are separate endpoints.

Run the installed-Agent matrix:

```bash
PYTHONPATH=src:. python3 \
  experiments/external_validity/run_multirepo_agent_benchmark.py \
  --workers 18 --timeout-seconds 210 \
  --output experiments/external_validity/results/multirepo-agent-confirmatory.json
```

Alternate checkouts can be supplied with repeated
`--repo repo-key=/absolute/path` options. The report freezes each source commit,
selected-file digest, Agent/model version, profile manifest, and probe digest.
Dirty working-tree files are ignored because snapshots come from `git show
COMMIT:path`; the dirty-path count remains a provenance covariate.

By default, repositories are resolved relative to the current user's home
directory. Set `SRI_BENCHMARK_ROOT=/path/to/checkouts` to use another common
root, and use `--repo` for repositories that do not follow the default layout.

Create the privacy-safe paired diagnostic views and score reconstruction:

```bash
PYTHONPATH=src:. python3 \
  experiments/external_validity/prepare_diagnostic_holdout.py \
  --source-report experiments/external_validity/results/multirepo-agent-confirmatory.json

PYTHONPATH=src:. python3 \
  experiments/external_validity/analyze_reconstruction_fidelity.py \
  --source-report experiments/external_validity/results/multirepo-agent-confirmatory.json
```

Run Raw, semantics-matched Raw, Panorama, and Graph+Model views through an
OpenAI-compatible model or the installed OpenCode model. Semantics-matched Raw
keeps the native record structure while adding the same named lifecycle,
record-kind, and evidence-grade contract exposed by Panorama. Graph-only is
evaluated deterministically inside every run:

```bash
PYTHONPATH=src:. python3 \
  experiments/external_validity/run_diagnostic_utility_study.py \
  --cases MULTIREPO_HOLDOUT.json --backend opencode \
  --model opencode/deepseek-v4-flash-free --workers 12
```

Generate the descriptive case counts and seven-template comparison used by the
paper. This script intentionally emits no case-level significance test because
rows within a condition template are strongly dependent:

```bash
python3 paper/analysis/paired_diagnostic_stats.py \
  experiments/external_validity/results/multirepo-diagnostic-qwen36-raw-semantic-inline-20260801.json \
  --right-report experiments/external_validity/results/multirepo-diagnostic-qwen36-confirmatory.json \
  --left-view raw_semantic --right-view panorama
```

The benchmark supports controlled mechanism-coverage claims across frozen
repository profiles and installed Agent systems. It does not estimate naturally occurring
incident prevalence, human usability, or causal Skill effectiveness.

Frozen confirmatory artifacts and their SHA-256 digests are recorded in
`confirmatory_manifest_20260801.json`. A failed gate is a retained result, not
an invitation to filter or silently retry rows.
